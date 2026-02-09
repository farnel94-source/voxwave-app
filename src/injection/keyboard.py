"""Injection de texte dans l'app active via clipboard + raccourci."""

import logging
import platform
import time
from typing import Literal

logger = logging.getLogger(__name__)


class TextInjector:
    """Injecte du texte dans l'app active."""

    def __init__(self, mode: Literal["paste", "type"] = "paste") -> None:
        self.mode = mode
        self.os_name = platform.system().lower()

    def inject(self, text: str) -> None:
        if not text:
            return
        if self.mode == "paste":
            self._inject_paste(text)
        else:
            self._inject_type(text)
        logger.info(f"Injecté ({len(text)} chars)")

    def _inject_paste(self, text: str) -> None:
        if self.os_name == "windows":
            self._inject_paste_win32(text)
        else:
            self._inject_paste_other(text)

    def _inject_paste_win32(self, text: str) -> None:
        """Injection Windows : pyperclip + keyboard.send('ctrl+v').

        La librairie `keyboard` gère correctement les low-level hooks
        (installés par pynput) qui empêchent SendInput de fonctionner
        dans d'autres applications.
        """
        import keyboard as kb
        import pyperclip

        # Étape 1 : Copier dans le clipboard
        pyperclip.copy(text)
        time.sleep(0.05)

        # Étape 2 : Vérifier le clipboard
        actual = pyperclip.paste()
        if actual != text:
            logger.warning(f"Clipboard mismatch: attendu {len(text)}, obtenu {len(actual)} chars")
            pyperclip.copy(text)
            time.sleep(0.05)
        else:
            logger.debug(f"Clipboard OK ({len(text)} chars)")

        # Étape 3 : Coller via keyboard.send (compatible avec les hooks pynput)
        time.sleep(0.05)
        kb.send('ctrl+v')
        logger.debug("keyboard.send('ctrl+v') envoyé")

    def _inject_paste_other(self, text: str) -> None:
        """Injection macOS/Linux via pyperclip + pynput."""
        import pyperclip

        pyperclip.copy(text)
        time.sleep(0.05)

        actual = pyperclip.paste()
        if actual != text:
            logger.warning(f"Clipboard mismatch: attendu {len(text)}, obtenu {len(actual)} chars")

        time.sleep(0.05)
        from pynput.keyboard import Controller, Key
        ctrl = Controller()
        mod = Key.cmd if self.os_name == "darwin" else Key.ctrl
        ctrl.press(mod)
        ctrl.press('v')
        time.sleep(0.02)
        ctrl.release('v')
        ctrl.release(mod)

    def _inject_type(self, text: str) -> None:
        import keyboard as kb
        kb.write(text, delay=0.01)
