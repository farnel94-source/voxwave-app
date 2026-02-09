"""Écoute des raccourcis clavier globaux."""

import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Écoute les hotkeys système avec debounce et protection anti-double."""

    DEBOUNCE_DELAY = 0.5  # secondes entre deux appuis F8

    def __init__(
        self,
        hotkey: str = "F8",
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
    ) -> None:
        self.hotkey = hotkey
        self.on_start = on_start
        self.on_stop = on_stop
        self._is_recording = False
        self._is_processing = False
        self._last_press_time = 0.0
        self._listener = None

    def _on_press(self, key):
        from pynput.keyboard import Key
        hotkey_map = {
            "F8": Key.f8, "F9": Key.f9, "F10": Key.f10,
            "F11": Key.f11, "F12": Key.f12,
        }
        target = hotkey_map.get(self.hotkey)
        if key != target:
            return

        # Debounce : ignorer les appuis trop rapprochés
        now = time.time()
        if now - self._last_press_time < self.DEBOUNCE_DELAY:
            logger.debug("Hotkey ignoré (debounce)")
            return
        self._last_press_time = now

        # Ignorer si le pipeline est en cours de traitement
        if self._is_processing:
            logger.debug("Hotkey ignoré (pipeline en cours)")
            return

        if not self._is_recording:
            self._is_recording = True
            logger.info("Enregistrement START")
            if self.on_start:
                self.on_start()
        else:
            self._is_recording = False
            logger.info("Enregistrement STOP")
            if self.on_stop:
                self.on_stop()

    def set_processing(self, state: bool) -> None:
        """Signale que le pipeline est en cours / terminé.

        Args:
            state: True = pipeline en cours, False = disponible.
        """
        self._is_processing = state

    def start(self) -> None:
        from pynput.keyboard import Listener
        self._listener = Listener(on_press=self._on_press)
        self._listener.start()
        logger.info(f"Hotkey listener démarré: {self.hotkey}")

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    @property
    def is_recording(self) -> bool:
        return self._is_recording
