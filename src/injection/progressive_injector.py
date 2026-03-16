"""Injection progressive : texte brut immédiat, puis remplacement par texte nettoyé.

Flow :
    1. inject_raw(raw_text)     → texte brut via clipboard + Ctrl+V (compatible tous apps)
    2. replace_with_clean(...)  → Backspace × N + Ctrl+V (paste texte nettoyé)

Stratégie Backspace × N :
    Contrairement à Shift+Left × N (défaillant sur Electron/Chromium à cause du timing
    asynchrone des events) et Ctrl+Z (qui crée des doublons en terminal et des
    comportements inattendus dans les apps Electron), Backspace est une touche simple
    sans modificateur → aucun problème de timing. Fonctionne dans VS Code, Terminal,
    Notepad, Word et toutes les apps Electron.

Garde-fous anti-effacement accidentel :
    Avant d'envoyer les Backspaces, deux conditions sont vérifiées :
    1. Délai < 1.5s depuis inject_raw (mesuré via time.monotonic(), immunisé aux ajustements NTP)
    2. Aucune action utilisateur (touche ou clic) depuis la fin de inject_raw
       → un listener pynput (clavier + souris) surveille en arrière-plan.
    Si une condition échoue → le texte brut est conservé en place (silent fallback).

Pourquoi sleep(0.1) après inject_raw :
    inject_raw envoie des events via pynput/clipboard. Sans buffer, replace_with_clean
    démarre avant que l'app cible ait traité le Ctrl+V → race condition.
    100ms garantit que le paste initial est visible dans l'app cible.

Usage:
    injector = ProgressiveInjector(text_injector)
    injector.inject_raw(raw_text)
    injector.replace_with_clean(raw_text, cloud_cleaner.clean_streaming(raw_text))
"""

import logging
import platform
import shutil
import subprocess
import time
from typing import Iterator

logger = logging.getLogger(__name__)


class ProgressiveInjector:
    """Injection en deux temps : brut immédiat → nettoyé via streaming.

    Réutilise le TextInjector existant pour l'injection de texte,
    et gère les backspaces de manière plateforme-agnostique.
    """

    def __init__(self, text_injector) -> None:
        """Initialise l'injecteur progressif.

        Args:
            text_injector: Instance de TextInjector (src/injection/keyboard.py).
        """
        self._injector = text_injector
        self._os_name = platform.system().lower()
        self._display_server: str = self._os_name

        if self._os_name == "linux":
            try:
                from src.utils.platform import get_display_server
                self._display_server = get_display_server()
            except Exception:
                self._display_server = "x11"  # fallback raisonnable sur Linux

        # Garde-fous anti-effacement accidentel
        self._inject_time: float = 0.0
        self._user_acted: bool = False
        self._user_watch_kb_listener = None    # pynput keyboard listener
        self._user_watch_mouse_listener = None  # pynput mouse listener

    def _inject_direct(self, text: str) -> bool:
        """Injecte via clipboard + pynput Ctrl+V (fiable sur tous apps Windows).

        Remplace keyboard.write() qui était défaillant sur Win11 Notepad (WinUI 3).
        pynput utilise un Controller isolé → pas de résidu Ctrl/Shift du hotkey.

        Returns:
            True si l'injection a réussi.
        """
        if self._os_name == "windows":
            try:
                import pyperclip
                from pynput.keyboard import Controller, Key
                # Retry clipboard copy (un autre process peut verrouiller le clipboard)
                clipboard_ok = False
                for attempt in range(3):
                    try:
                        pyperclip.copy(text)
                        # Vérifier que le clipboard contient bien notre texte
                        if pyperclip.paste() == text:
                            clipboard_ok = True
                            break
                    except Exception:
                        pass
                    if attempt < 2:  # pas de sleep sur la dernière tentative
                        time.sleep(0.05)
                if not clipboard_ok:
                    logger.warning("Clipboard non fiable après 3 tentatives, fallback inject()")
                    return False
                time.sleep(0.05)  # laisser le clipboard se stabiliser
                ctrl = Controller()
                ctrl.press(Key.ctrl)
                ctrl.press('v')
                time.sleep(0.01)
                ctrl.release('v')
                ctrl.release(Key.ctrl)
                time.sleep(0.05)  # laisser l'app cible traiter le Ctrl+V
                return True
            except Exception as e:
                logger.warning(f"pynput inject échoué: {e}, fallback inject()")
        return False

    def inject_raw(self, text: str) -> None:
        """Injecte le texte brut immédiatement dans l'application active.

        Utilise clipboard + Ctrl+V (compatible tous apps y compris Notepad).
        Le sleep(0.1) garantit que l'app cible a traité le Ctrl+V avant que
        replace_with_clean ne démarre. Après le sleep, démarre la surveillance
        clavier + souris pour détecter toute action utilisateur.

        Args:
            text: Texte brut (sortie Groq, non nettoyé).
        """
        if not text:
            return
        # Sauvegarder le clipboard avant d'écraser (restauré après le paste).
        # Après restauration, replace_with_clean() sauvegarde le contenu original
        # (et non raw_text) — les deux restaurations sont ainsi cohérentes.
        saved_clipboard: str | None = None
        try:
            import pyperclip
            saved_clipboard = pyperclip.paste()
        except Exception:
            pass
        if not self._inject_direct(text):
            self._injector.inject(text)
        # Buffer : s'assurer que l'app cible a traité le Ctrl+V
        # 200ms : certaines apps (Electron, WinUI3) sont lentes à traiter le paste
        time.sleep(0.2)
        # Restaurer le clipboard original (le texte dicté est déjà dans l'app cible)
        if saved_clipboard is not None:
            try:
                import pyperclip  # noqa: F811 — re-import sûr (module mis en cache)
                pyperclip.copy(saved_clipboard)
            except Exception:
                pass
        logger.info(f"Texte brut injecté : {len(text)} chars")
        # Démarrer la surveillance et horodater pour les garde-fous de replace_with_clean
        self._inject_time = time.monotonic()
        self._user_acted = False
        self._start_user_watch()

    def replace_with_clean(
        self, raw_text: str, clean_generator: Iterator[str]
    ) -> None:
        """Remplace le texte brut par le texte nettoyé via streaming.

        Accumule les tokens du stream, vérifie les deux garde-fous, puis :
        1. Backspace × len(raw_text) — efface le texte brut caractère par caractère
        2. Ctrl+V — colle le texte nettoyé

        Garde-fous (vérifiés dans cet ordre) :
        1. Délai < 1.5s depuis inject_raw (time.monotonic(), immunisé aux ajustements NTP)
        2. Aucune action utilisateur (touche ou clic) depuis inject_raw
        → Si une condition échoue : _stop_user_watch() + return (texte brut conservé).

        Args:
            raw_text: Texte brut précédemment injecté (pour compter les backspaces).
            clean_generator: Générateur de tokens depuis OpenAI streaming.
        """
        # Accumuler tous les tokens — le stream est rapide (~300ms)
        try:
            clean_text = "".join(clean_generator).strip()
        except Exception as e:
            self._stop_user_watch()
            logger.warning(f"Erreur accumulation stream nettoyage: {e}, texte brut conservé")
            return

        if not clean_text:
            self._stop_user_watch()
            logger.warning("Texte nettoyé vide après streaming, texte brut conservé")
            return

        # ── Garde-fous : vérifier AVANT de stopper la surveillance ───────────
        elapsed = time.monotonic() - self._inject_time
        if elapsed > 1.5:
            self._stop_user_watch()
            logger.warning(f"Remplacement ignoré : délai dépassé ({elapsed:.1f}s)")
            return

        if self._user_acted:
            self._stop_user_watch()
            logger.warning("Remplacement ignoré : action utilisateur détectée")
            return

        # Stopper la surveillance juste avant d'agir
        self._stop_user_watch()

        import pyperclip
        # Sauvegarder le clipboard original (sera restauré après le coller)
        try:
            saved_clipboard = pyperclip.paste()
        except Exception:
            saved_clipboard = None

        # Copier le texte nettoyé dans le clipboard
        try:
            pyperclip.copy(clean_text)
        except Exception as e:
            logger.warning(f"Clipboard copy échoué: {e}, annulation remplacement")
            return

        # ── Remplacement : Backspace × N + Ctrl+V ────────────────────────────
        # Backspace = touche simple sans modificateur → aucun problème de timing
        # Fonctionne dans VS Code, Terminal, Notepad, Word et toutes les apps Electron.
        self._send_backspaces(len(raw_text))
        time.sleep(0.35)  # 350ms : WinUI3 traite WM_CLIPBOARDUPDATE en async — les derniers
        # backspaces peuvent arriver après le Ctrl+V si le buffer est trop court
        self._send_ctrl_v()

        logger.info(
            f"Texte remplacé : {len(raw_text)} chars bruts → {len(clean_text)} chars nettoyés"
        )

        # Restaurer le clipboard original
        if saved_clipboard is not None:
            time.sleep(0.3)
            try:
                pyperclip.copy(saved_clipboard)
            except Exception:
                pass

    # ── Sélection en arrière ──────────────────────────────────────────────────

    def _select_backward(self, count: int) -> None:
        """Sélectionne N caractères en arrière (Shift+Left × N).

        Args:
            count: Nombre de caractères à sélectionner.
        """
        if count <= 0:
            return
        logger.debug(f"Sélection de {count} chars en arrière (plateforme: {self._display_server})")
        if self._os_name == "linux" and self._display_server == "wayland":
            self._select_backward_wayland(count)
        elif self._os_name == "linux":
            self._select_backward_x11(count)
        else:
            self._select_backward_windows(count)

    def _select_backward_windows(self, count: int) -> None:
        """Shift+Left × N via pynput (états modificateurs isolés, pas de résidu Ctrl/Shift).

        Remplace keyboard.send('shift+left') qui héritait du résidu Ctrl du hotkey,
        transformant Shift+Left en Ctrl+Shift+Left (sélection par mot au lieu de caractère).
        """
        try:
            from pynput.keyboard import Controller, Key
            ctrl = Controller()
            ctrl.press(Key.shift)
            for _ in range(count):
                ctrl.press(Key.left)
                ctrl.release(Key.left)
                time.sleep(0.002)
            ctrl.release(Key.shift)
        except Exception as e:
            logger.warning(f"select_backward pynput échoué: {e}")

    def _select_backward_x11(self, count: int) -> None:
        """Shift+Left × N via xdotool --repeat (X11)."""
        if shutil.which("xdotool"):
            subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "--repeat", str(count), "shift+Left"],
                timeout=10, check=False,
            )
        else:
            self._select_backward_windows(count)

    def _select_backward_wayland(self, count: int) -> None:
        """Shift+Left × N via wtype ou ydotool (Wayland)."""
        if shutil.which("wtype"):
            args = ["wtype"] + ["-M", "shift", "-k", "Left", "-m", "shift"] * count
            subprocess.run(args, timeout=10, check=False)
        elif shutil.which("ydotool"):
            for _ in range(count):
                subprocess.run(
                    ["ydotool", "key", "42:1", "105:1", "105:0", "42:0"],
                    timeout=2, check=False,
                )
        else:
            self._select_backward_windows(count)

    # ── Surveillance action utilisateur ──────────────────────────────────────

    def _start_user_watch(self) -> None:
        """Démarre deux listeners pynput (clavier + souris) pour détecter toute action utilisateur.

        Dès qu'une touche est pressée ou qu'un clic souris est effectué, _user_acted
        est mis à True et le listener correspondant se stoppe immédiatement.
        Le délai est mesuré côté replace_with_clean via time.monotonic().
        """
        try:
            from pynput import keyboard as kb, mouse

            def on_key(key):
                self._user_acted = True
                return False  # stoppe le kb.Listener immédiatement

            def on_click(x, y, button, pressed):
                if pressed:
                    self._user_acted = True
                    return False  # stoppe le mouse.Listener immédiatement

            self._user_watch_kb_listener = kb.Listener(on_press=on_key)
            self._user_watch_mouse_listener = mouse.Listener(on_click=on_click)
            self._user_watch_kb_listener.start()
            self._user_watch_mouse_listener.start()
        except Exception as e:
            logger.debug(f"user_watch non démarré : {e}")

    def _stop_user_watch(self) -> None:
        """Arrête les deux listeners (clavier + souris) s'ils sont actifs."""
        for attr in ("_user_watch_kb_listener", "_user_watch_mouse_listener"):
            listener = getattr(self, attr, None)
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass
                setattr(self, attr, None)

    # ── Coller (Ctrl+V) ───────────────────────────────────────────────────────

    def _send_ctrl_v(self) -> None:
        """Envoie Ctrl+V selon la plateforme."""
        if self._os_name == "linux" and self._display_server == "wayland":
            if shutil.which("wtype"):
                subprocess.run(["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"], timeout=3, check=False)
            elif shutil.which("ydotool"):
                subprocess.run(["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], timeout=3, check=False)
            else:
                self._do_pynput_paste()
        elif self._os_name == "linux":
            if shutil.which("xdotool"):
                subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"], timeout=3, check=False)
            else:
                self._do_pynput_paste()
        else:
            # pynput directement — keyboard lib problématique sur Win11 Notepad (WinUI 3)
            self._do_pynput_paste()

    def _do_pynput_paste(self) -> None:
        """Colle via pynput (fallback universel)."""
        try:
            from pynput.keyboard import Controller, Key
            ctrl = Controller()
            ctrl.press(Key.ctrl)
            ctrl.press('v')
            time.sleep(0.02)
            ctrl.release('v')
            ctrl.release(Key.ctrl)
        except Exception as e:
            logger.warning(f"pynput paste échoué: {e}")

    # ── Backspaces ────────────────────────────────────────────────────────────

    def _send_backspaces(self, count: int) -> None:
        """Envoie N touches Backspace selon la plateforme.

        Args:
            count: Nombre de backspaces à envoyer.
        """
        if count <= 0:
            return

        logger.debug(f"Envoi de {count} backspaces (plateforme: {self._display_server})")

        if self._os_name == "linux" and self._display_server == "wayland":
            self._backspace_wayland(count)
        elif self._os_name == "linux":
            self._backspace_x11(count)
        else:
            self._backspace_pynput(count)

    def _backspace_wayland(self, count: int) -> None:
        """Backspaces via wtype sur Wayland (une seule commande pour tous)."""
        if shutil.which("wtype"):
            # Construire la liste d'arguments : ["-k", "BackSpace"] × count
            args = ["wtype"] + ["-k", "BackSpace"] * count
            subprocess.run(args, timeout=10, check=False)
        elif shutil.which("ydotool"):
            # ydotool : keycode 14 = BackSpace
            for _ in range(count):
                subprocess.run(
                    ["ydotool", "key", "14:1", "14:0"],
                    timeout=2, check=False,
                )
        else:
            self._backspace_pynput(count)

    def _backspace_x11(self, count: int) -> None:
        """Backspaces via xdotool --repeat sur X11 (plus rapide qu'un loop)."""
        if shutil.which("xdotool"):
            subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "--repeat", str(count), "BackSpace"],
                timeout=10, check=False,
            )
        else:
            self._backspace_pynput(count)

    def _backspace_pynput(self, count: int) -> None:
        """Backspaces via pynput (compatible WinUI3 Notepad — keyboard lib problématique)."""
        try:
            from pynput.keyboard import Controller, Key
            ctrl = Controller()
            for _ in range(count):
                ctrl.press(Key.backspace)
                ctrl.release(Key.backspace)
                time.sleep(0.002)  # 2ms — évite que Windows "mange" des backspaces
        except Exception as e:
            logger.warning(f"pynput backspace échoué: {e}")
