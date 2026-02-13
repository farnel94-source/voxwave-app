"""Injection de texte dans l'app active via clipboard + raccourci.

Supporte Windows, macOS, Linux X11 (xdotool) et Linux Wayland (wtype).
Le clipboard original est sauvegarde et restaure apres injection.
"""

import logging
import platform
import shutil
import subprocess
import time
from typing import Literal, Optional

logger = logging.getLogger(__name__)


class TextInjector:
    """Injecte du texte dans l'app active."""

    def __init__(self, mode: Literal["paste", "type"] = "paste") -> None:
        self.mode = mode
        self.os_name = platform.system().lower()
        if self.os_name == "linux":
            from src.utils.platform import get_display_server
            self._display_server = get_display_server()
            self._check_clipboard_tools()
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

    @staticmethod
    def _save_clipboard() -> Optional[str]:
        """Sauvegarde le contenu actuel du clipboard."""
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception:
            logger.debug("Impossible de lire le clipboard")
            return None

    @staticmethod
    def _restore_clipboard(content: Optional[str]) -> None:
        """Restaure le clipboard a son contenu original."""
        if content is not None:
            try:
                import pyperclip
                time.sleep(0.3)
                pyperclip.copy(content)
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
        logger.info(f"Injecte ({len(text)} chars)")

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
        import pyperclip

        original = self._save_clipboard()
        try:
            pyperclip.copy(text)
            time.sleep(0.05)

            actual = pyperclip.paste()
            if actual != text:
                logger.warning(f"Clipboard mismatch: attendu {len(text)}, obtenu {len(actual)} chars")
                pyperclip.copy(text)
                time.sleep(0.05)
            else:
                logger.debug(f"Clipboard OK ({len(text)} chars)")

            time.sleep(0.05)
            kb.send('ctrl+v')
            logger.debug("keyboard.send('ctrl+v') envoye")
        finally:
            self._restore_clipboard(original)

    def _inject_paste_wayland(self, text: str) -> None:
        """Injection Wayland : wl-copy + wtype Ctrl+V."""
        import pyperclip

        original = self._save_clipboard()
        try:
            pyperclip.copy(text)
            time.sleep(0.05)

            if shutil.which("wtype"):
                subprocess.run(
                    ["wtype", "-M", "ctrl", "v", "-m", "ctrl"],
                    timeout=5, check=False,
                )
            else:
                logger.error("wtype non disponible, injection impossible sur Wayland")
        finally:
            self._restore_clipboard(original)

    def _inject_paste_x11(self, text: str) -> None:
        """Injection X11 : pyperclip + xdotool key ctrl+v."""
        import pyperclip

        original = self._save_clipboard()
        try:
            pyperclip.copy(text)
            time.sleep(0.05)

            if shutil.which("xdotool"):
                subprocess.run(
                    ["xdotool", "key", "ctrl+v"],
                    timeout=5, check=False,
                )
            else:
                # Fallback pynput
                self._do_pynput_paste()
        finally:
            self._restore_clipboard(original)

    def _inject_paste_pynput(self, text: str) -> None:
        """Injection macOS/fallback via pyperclip + pynput."""
        import pyperclip

        original = self._save_clipboard()
        try:
            pyperclip.copy(text)
            time.sleep(0.05)

            actual = pyperclip.paste()
            if actual != text:
                logger.warning(f"Clipboard mismatch: attendu {len(text)}, obtenu {len(actual)} chars")

            time.sleep(0.05)
            self._do_pynput_paste()
        finally:
            self._restore_clipboard(original)

    def _do_pynput_paste(self) -> None:
        """Execute le Ctrl+V / Cmd+V via pynput."""
        from pynput.keyboard import Controller, Key
        ctrl = Controller()
        mod = Key.cmd if self.os_name == "darwin" else Key.ctrl
        ctrl.press(mod)
        ctrl.press('v')
        time.sleep(0.02)
        ctrl.release('v')
        ctrl.release(mod)

    def _inject_type(self, text: str) -> None:
        """Injection par frappe clavier."""
        if self.os_name == "linux" and self._display_server == "wayland":
            if shutil.which("wtype"):
                subprocess.run(["wtype", text], timeout=10, check=False)
            else:
                logger.error("wtype non disponible pour la frappe Wayland")
        else:
            import keyboard as kb
            kb.write(text, delay=0.01)
