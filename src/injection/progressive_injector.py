"""Injection progressive : texte brut immédiat, puis remplacement par texte nettoyé.

Flow :
    1. inject_raw(raw_text)     → texte brut visible en < 800ms
    2. replace_with_clean(...)  → N backspaces + injection texte nettoyé (~1.1s total)

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

    def inject_raw(self, text: str) -> None:
        """Injecte le texte brut immédiatement dans l'application active.

        Args:
            text: Texte brut (sortie Groq, non nettoyé).
        """
        if not text:
            return
        self._injector.inject(text)
        logger.info(f"Texte brut injecté : {len(text)} chars")

    def replace_with_clean(
        self, raw_text: str, clean_generator: Iterator[str]
    ) -> None:
        """Remplace le texte brut par le texte nettoyé via streaming.

        Accumule les tokens du stream, puis :
        1. Envoie len(raw_text) touches Backspace pour effacer le brut
        2. Injecte le texte nettoyé complet d'un coup

        Args:
            raw_text: Texte brut précédemment injecté (pour compter les backspaces).
            clean_generator: Générateur de tokens depuis OpenAI streaming.
        """
        # Accumuler tous les tokens — le stream est rapide (~300ms)
        try:
            clean_text = "".join(clean_generator).strip()
        except Exception as e:
            logger.warning(f"Erreur accumulation stream nettoyage: {e}, texte brut conservé")
            return

        if not clean_text:
            logger.warning("Texte nettoyé vide après streaming, texte brut conservé")
            return

        # Supprimer le texte brut caractère par caractère
        self._send_backspaces(len(raw_text))

        # Petit délai pour laisser les backspaces s'appliquer dans l'app cible
        time.sleep(0.05)

        # Injecter le texte nettoyé
        self._injector.inject(clean_text)
        logger.info(
            f"Texte remplacé : {len(raw_text)} chars bruts → {len(clean_text)} chars nettoyés"
        )

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
        """Backspaces via pynput (Windows + fallback Linux)."""
        try:
            from pynput.keyboard import Controller, Key
            ctrl = Controller()
            for _ in range(count):
                ctrl.press(Key.backspace)
                ctrl.release(Key.backspace)
        except Exception as e:
            logger.warning(f"pynput backspace échoué: {e}")
