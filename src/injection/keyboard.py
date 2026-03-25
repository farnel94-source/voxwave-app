"""Injection de texte dans l'app active via clipboard + raccourci.

Supporte Windows et Linux (X11 xdotool + Wayland wtype).
Le clipboard original est sauvegarde et restaure apres injection.
Note: macOS n'est pas supporte — VoxWave cible Windows et Linux.
"""

import logging
import platform
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Callable, Literal, Optional, TypeVar

logger = logging.getLogger(__name__)

if sys.platform == "darwin":
    logger.warning("VoxWave ne supporte pas macOS. L'injection clavier peut ne pas fonctionner.")

T = TypeVar("T")


def _with_timeout(func: Callable[..., T], timeout: float, default: T, *args: Any, **kwargs: Any) -> T:
    """Execute une fonction avec timeout via ThreadPoolExecutor.

    Args:
        func: Fonction a executer.
        timeout: Timeout en secondes.
        default: Valeur retournee si timeout.
        *args: Arguments positionnels pour func.
        **kwargs: Arguments nommes pour func.

    Returns:
        Resultat de func ou default si timeout.
    """
    func_name = getattr(func, "__name__", repr(func))
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func, *args, **kwargs)
    try:
        return future.result(timeout=timeout)
    except FutureTimeoutError:
        logger.warning(f"Timeout ({timeout}s) sur {func_name}, valeur par defaut utilisee")
        return default
    except Exception as e:
        logger.warning(f"Erreur sur {func_name}: {e}")
        return default
    finally:
        executor.shutdown(wait=False)


class TextInjector:
    """Injecte du texte dans l'app active."""

    def __init__(self, mode: Literal["paste", "type"] = "paste") -> None:
        self.mode = mode
        self.os_name = platform.system().lower()
        self._wayland_paste_tool: Optional[str] = None
        self._wayland_type_tool: Optional[str] = None
        if self.os_name == "linux":
            from src.utils.platform import get_display_server
            self._display_server = get_display_server()
            self._check_clipboard_tools()
            if self._display_server == "wayland":
                self._detect_wayland_tools()
        else:
            self._display_server = self.os_name

    def _check_clipboard_tools(self) -> None:
        """Verifie que les outils clipboard sont disponibles sur Linux."""
        if self._display_server == "wayland":
            if not shutil.which("wl-copy"):
                logger.warning(
                    "wl-copy non trouve. Installez wl-clipboard pour le support Wayland: "
                    "sudo apt install wl-clipboard"
                )
            if not shutil.which("wtype"):
                logger.warning(
                    "wtype non trouve. Installez wtype pour l'injection texte Wayland: "
                    "sudo apt install wtype"
                )
        elif self._display_server == "x11":
            if not shutil.which("xdotool"):
                logger.warning(
                    "xdotool non trouve. Installez-le pour l'injection texte X11: "
                    "sudo apt install xdotool"
                )
            if not shutil.which("xclip") and not shutil.which("xsel"):
                logger.warning(
                    "xclip/xsel non trouve. Installez xclip pour le clipboard X11: "
                    "sudo apt install xclip"
                )

    def _detect_wayland_tools(self) -> None:
        """Detecte les outils disponibles pour Wayland et etablit la cascade.

        Paste: wtype → ydotool → pynput (XWayland apps)
        Type:  wtype → ydotool → None (erreur explicite)
        """
        # Cascade paste
        if shutil.which("wtype"):
            self._wayland_paste_tool = "wtype"
        elif shutil.which("ydotool"):
            self._wayland_paste_tool = "ydotool"
            logger.info("wtype non trouve, utilisation de ydotool pour le paste Wayland")
        else:
            self._wayland_paste_tool = "pynput"
            logger.warning(
                "wtype et ydotool non trouves. Fallback pynput (XWayland uniquement). "
                "Installez wtype: sudo apt install wtype"
            )

        # Cascade type
        if shutil.which("wtype"):
            self._wayland_type_tool = "wtype"
        elif shutil.which("ydotool"):
            self._wayland_type_tool = "ydotool"
            logger.info("wtype non trouve, utilisation de ydotool pour la frappe Wayland")
        else:
            self._wayland_type_tool = None
            logger.warning(
                "Aucun outil de frappe Wayland disponible. "
                "Installez wtype (sudo apt install wtype) ou ydotool (sudo apt install ydotool)"
            )

        logger.info(f"Wayland tools: paste={self._wayland_paste_tool}, type={self._wayland_type_tool}")

    @staticmethod
    def _save_clipboard() -> Optional[str]:
        """Sauvegarde le contenu actuel du clipboard (avec timeout 2s)."""
        try:
            import pyperclip
            return _with_timeout(pyperclip.paste, 2.0, None)
        except Exception:
            logger.debug("Impossible de lire le clipboard")
            return None

    @staticmethod
    def _copy_to_clipboard(text: str) -> None:
        """Copie du texte dans le clipboard (avec timeout 2s).

        Args:
            text: Texte a copier.
        """
        import pyperclip
        _with_timeout(pyperclip.copy, 2.0, None, text)

    @staticmethod
    def _paste_from_clipboard() -> Optional[str]:
        """Lit le clipboard (avec timeout 2s).

        Returns:
            Contenu du clipboard ou None si timeout.
        """
        import pyperclip
        return _with_timeout(pyperclip.paste, 2.0, None)

    @staticmethod
    def _restore_clipboard(content: Optional[str]) -> None:
        """Restaure le clipboard a son contenu original (avec timeout 2s)."""
        if content is not None:
            try:
                import pyperclip
                time.sleep(0.3)
                _with_timeout(pyperclip.copy, 2.0, None, content)
                logger.debug("Clipboard restaure")
            except Exception:
                logger.warning("Impossible de restaurer le clipboard")

    def inject(self, text: str) -> None:
        """Injecte du texte dans l'application active.

        Args:
            text: Texte a injecter.
        """
        if not text:
            return
        if self.mode == "paste":
            self._inject_paste(text)
        else:
            self._inject_type(text)
        preview = text[:20] + "..." if len(text) > 20 else text
        logger.debug("Texte injecte (%d chars): %s", len(text), preview)

    def _inject_paste(self, text: str) -> None:
        """Injecte via clipboard + paste selon la plateforme."""
        if self.os_name == "windows":
            self._inject_paste_win32(text)
        elif self.os_name == "linux":
            if self._display_server == "wayland":
                self._inject_paste_wayland(text)
            elif self._display_server == "x11":
                self._inject_paste_x11(text)
            else:
                self._inject_paste_pynput(text)
        else:
            self._inject_paste_pynput(text)

    def _inject_paste_win32(self, text: str) -> None:
        """Injection Windows : pyperclip + keyboard.send('ctrl+v')."""
        import keyboard as kb

        original = self._save_clipboard()
        try:
            self._copy_to_clipboard(text)
            time.sleep(0.05)

            actual = self._paste_from_clipboard()
            if actual != text:
                logger.warning(f"Clipboard mismatch: attendu {len(text)}, obtenu {len(actual) if actual else 0} chars")
                self._copy_to_clipboard(text)
                time.sleep(0.05)
            else:
                logger.debug(f"Clipboard OK ({len(text)} chars)")

            time.sleep(0.05)
            kb.send('ctrl+v')
            logger.debug("keyboard.send('ctrl+v') envoye")
        finally:
            self._restore_clipboard(original)

    def _inject_paste_wayland(self, text: str) -> None:
        """Injection Wayland : wl-copy + wtype/ydotool/pynput Ctrl+V."""
        original = self._save_clipboard()
        try:
            self._copy_to_clipboard(text)
            time.sleep(0.05)

            if self._wayland_paste_tool == "wtype":
                subprocess.run(
                    ["wtype", "-M", "ctrl", "v", "-m", "ctrl"],
                    timeout=5, check=False,
                )
            elif self._wayland_paste_tool == "ydotool":
                # ydotool keycodes: ctrl=29, v=47
                subprocess.run(
                    ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
                    timeout=5, check=False,
                )
            elif self._wayland_paste_tool == "pynput":
                self._do_pynput_paste()
            else:
                logger.error(
                    "Aucun outil d'injection disponible sur Wayland. "
                    "Installez wtype (sudo apt install wtype) ou ydotool (sudo apt install ydotool)"
                )
        finally:
            self._restore_clipboard(original)

    def _inject_paste_x11(self, text: str) -> None:
        """Injection X11 : pyperclip + xdotool key ctrl+v, fallback xdotool type."""
        original = self._save_clipboard()
        try:
            self._copy_to_clipboard(text)
            time.sleep(0.05)

            # Verifier que le clipboard a bien ete ecrit
            import pyperclip
            try:
                clipboard_ok = _with_timeout(pyperclip.paste, 1.0, "") == text
            except Exception:
                clipboard_ok = False

            if clipboard_ok:
                if shutil.which("xdotool"):
                    subprocess.run(
                        ["xdotool", "key", "ctrl+v"],
                        timeout=5, check=False,
                    )
                else:
                    self._do_pynput_paste()
            else:
                # Clipboard indisponible (xclip manquant) — fallback injection directe
                logger.warning("Clipboard indisponible, fallback xdotool type")
                if shutil.which("xdotool"):
                    subprocess.run(
                        ["xdotool", "type", "--clearmodifiers", "--delay", "12", text],
                        timeout=10, check=False,
                    )
                else:
                    self._do_pynput_paste()
        finally:
            self._restore_clipboard(original)

    def _inject_paste_pynput(self, text: str) -> None:
        """Injection macOS/fallback via pyperclip + pynput."""
        original = self._save_clipboard()
        try:
            self._copy_to_clipboard(text)
            time.sleep(0.05)

            actual = self._paste_from_clipboard()
            if actual != text:
                logger.warning(f"Clipboard mismatch: attendu {len(text)}, obtenu {len(actual) if actual else 0} chars")

            time.sleep(0.05)
            self._do_pynput_paste()
        finally:
            self._restore_clipboard(original)

    def _do_pynput_paste(self) -> None:
        """Execute le Ctrl+V / Cmd+V via pynput (avec timeout 3s)."""
        def _paste_action() -> None:
            from pynput.keyboard import Controller, Key
            ctrl = Controller()
            mod = Key.cmd if self.os_name == "darwin" else Key.ctrl
            ctrl.press(mod)
            ctrl.press('v')
            time.sleep(0.02)
            ctrl.release('v')
            ctrl.release(mod)
        _with_timeout(_paste_action, 3.0, None)

    def _inject_type(self, text: str) -> None:
        """Injection par frappe clavier."""
        if self.os_name == "linux" and self._display_server == "wayland":
            if self._wayland_type_tool == "wtype":
                subprocess.run(["wtype", text], timeout=10, check=False)
            elif self._wayland_type_tool == "ydotool":
                subprocess.run(["ydotool", "type", text], timeout=10, check=False)
            else:
                logger.error(
                    "Aucun outil de frappe Wayland disponible. "
                    "Installez wtype (sudo apt install wtype) ou ydotool (sudo apt install ydotool)"
                )
        else:
            import keyboard as kb
            kb.write(text, delay=0.01)
