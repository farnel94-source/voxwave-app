"""Ecoute des raccourcis clavier globaux.

Supporte pynput (Windows, macOS, X11) et evdev (Linux Wayland/X11).
"""

import logging
import sys
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Ecoute les hotkeys systeme avec debounce et protection anti-double.

    Selectionne automatiquement le backend :
    - evdev pour Linux Wayland (et X11 en fallback)
    - pynput pour Windows, macOS, et X11
    """

    def __init__(
        self,
        hotkey: str = "F8",
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        debounce_delay: float = 0.5,
    ) -> None:
        self.hotkey = hotkey
        self.on_start = on_start
        self.on_stop = on_stop
        self.debounce_delay = debounce_delay
        self._is_recording = False
        self._is_processing = False
        self._last_press_time = 0.0
        self._listener = None
        self._lock = threading.Lock()
        self._backend: str = self._detect_backend()

    @staticmethod
    def _detect_backend() -> str:
        """Detecte le backend hotkey a utiliser.

        Returns:
            'evdev' pour Linux Wayland, 'pynput' sinon.
        """
        if sys.platform != "linux":
            return "pynput"
        from src.utils.platform import get_display_server
        display = get_display_server()
        if display == "wayland":
            try:
                import evdev  # noqa: F401
                logger.info("Backend hotkey: evdev (Wayland)")
                return "evdev"
            except ImportError:
                logger.warning("evdev non disponible, fallback pynput")
                return "pynput"
        return "pynput"

    def _handle_hotkey(self) -> None:
        """Logique commune de gestion du hotkey (toggle recording)."""
        with self._lock:
            now = time.monotonic()
            if now - self._last_press_time < self.debounce_delay:
                logger.debug("Hotkey ignore (debounce)")
                return
            self._last_press_time = now

            if self._is_processing:
                logger.debug("Hotkey ignore (pipeline en cours)")
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

    def _on_press_pynput(self, key) -> None:
        """Callback pynput pour les appuis clavier."""
        from pynput.keyboard import Key
        hotkey_map = {
            "F8": Key.f8, "F9": Key.f9, "F10": Key.f10,
            "F11": Key.f11, "F12": Key.f12,
        }
        target = hotkey_map.get(self.hotkey)
        if key != target:
            return
        self._handle_hotkey()

    def _run_evdev(self) -> None:
        """Boucle de lecture evdev (tourne dans un thread daemon)."""
        import evdev
        from evdev import ecodes

        hotkey_map = {
            "F8": ecodes.KEY_F8, "F9": ecodes.KEY_F9, "F10": ecodes.KEY_F10,
            "F11": ecodes.KEY_F11, "F12": ecodes.KEY_F12,
        }
        target_code = hotkey_map.get(self.hotkey)
        if target_code is None:
            logger.error(f"Hotkey {self.hotkey} non supporte avec evdev")
            return

        # Trouver les devices clavier
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        keyboards = [
            d for d in devices
            if ecodes.EV_KEY in (d.capabilities().keys() if hasattr(d.capabilities(), 'keys') else d.capabilities())
        ]

        if not keyboards:
            logger.error("Aucun clavier evdev detecte. L'utilisateur est-il dans le groupe 'input' ?")
            return

        logger.info(f"evdev: ecoute sur {len(keyboards)} peripherique(s)")
        import selectors
        sel = selectors.DefaultSelector()
        for kbd in keyboards:
            sel.register(kbd, selectors.EVENT_READ)

        self._evdev_running = True
        while self._evdev_running:
            events = sel.select(timeout=0.5)
            for key_sel, mask in events:
                device = key_sel.fileobj
                try:
                    for event in device.read():
                        if event.type == ecodes.EV_KEY and event.value == 1:  # key down
                            if event.code == target_code:
                                self._handle_hotkey()
                except OSError:
                    logger.warning(f"Device evdev perdu: {device.path}")
                    sel.unregister(device)

        sel.close()
        for kbd in keyboards:
            try:
                kbd.close()
            except Exception:
                pass

    def set_processing(self, state: bool) -> None:
        """Signale que le pipeline est en cours / termine.

        Args:
            state: True = pipeline en cours, False = disponible.
        """
        self._is_processing = state

    def start(self) -> None:
        """Demarre l'ecoute du hotkey."""
        if self._backend == "evdev":
            import threading
            self._evdev_running = True
            self._listener = threading.Thread(target=self._run_evdev, daemon=True)
            self._listener.start()
            logger.info(f"Hotkey listener demarre (evdev): {self.hotkey}")
        else:
            from pynput.keyboard import Listener
            self._listener = Listener(on_press=self._on_press_pynput)
            self._listener.start()
            logger.info(f"Hotkey listener demarre (pynput): {self.hotkey}")

    def stop(self) -> None:
        """Arrete l'ecoute du hotkey."""
        if self._backend == "evdev":
            self._evdev_running = False
            if self._listener:
                self._listener.join(timeout=2)
                self._listener = None
        else:
            if self._listener:
                self._listener.stop()
                self._listener = None

    @property
    def is_recording(self) -> bool:
        return self._is_recording
