"""Ecoute des raccourcis clavier globaux.

Supporte pynput (Windows, macOS, X11) et evdev (Linux Wayland/X11).
Supporte les combos : F8, Ctrl+Shift+V, Alt+R, etc.
"""

import logging
import sys
import threading
import time
from typing import Callable, FrozenSet, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Mapping des noms de modifiers vers les objets pynput Key
_PYNPUT_MODIFIER_MAP: dict = {}  # rempli lazily dans _init_pynput_maps
_PYNPUT_KEY_MAP: dict = {}


def _init_pynput_maps() -> None:
    """Initialise les maps pynput (lazy, importe pynput une seule fois)."""
    global _PYNPUT_MODIFIER_MAP, _PYNPUT_KEY_MAP
    if _PYNPUT_MODIFIER_MAP:
        return
    from pynput.keyboard import Key
    _PYNPUT_MODIFIER_MAP = {
        "ctrl": {Key.ctrl_l, Key.ctrl_r, Key.ctrl},
        "shift": {Key.shift_l, Key.shift_r, Key.shift},
        "alt": {Key.alt_l, Key.alt_r, Key.alt},
        "cmd": {Key.cmd_l, Key.cmd_r, Key.cmd} if hasattr(Key, "cmd") else set(),
        "super": {Key.cmd_l, Key.cmd_r, Key.cmd} if hasattr(Key, "cmd") else set(),
    }
    _PYNPUT_KEY_MAP = {
        f"f{i}": getattr(Key, f"f{i}") for i in range(1, 13)
    }


def parse_hotkey(hotkey_str: str) -> Tuple[FrozenSet[str], str]:
    """Parse une chaine hotkey en (modifiers, main_key).

    Exemples:
        "F8" -> (frozenset(), "f8")
        "Ctrl+Shift+V" -> (frozenset({"ctrl", "shift"}), "v")
        "Alt+R" -> (frozenset({"alt"}), "r")

    Args:
        hotkey_str: Chaine hotkey (ex: "Ctrl+Shift+V").

    Returns:
        Tuple (frozenset de noms de modifiers en minuscules, main_key en minuscules).

    Raises:
        ValueError: Si le format est invalide.
    """
    parts = [p.strip().lower() for p in hotkey_str.split("+")]
    if not parts:
        raise ValueError(f"Hotkey vide: {hotkey_str}")

    known_modifiers = {"ctrl", "shift", "alt", "cmd", "super"}
    modifiers = frozenset(p for p in parts[:-1] if p in known_modifiers)
    main_key = parts[-1]

    if main_key in known_modifiers and len(parts) == 1:
        raise ValueError(f"Hotkey ne peut pas etre un modifier seul: {hotkey_str}")

    return modifiers, main_key


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
        self.on_start = on_start
        self.on_stop = on_stop
        self.debounce_delay = debounce_delay
        self._is_recording = False
        self._is_processing = False
        self._last_press_time = 0.0
        self._listener = None
        self._lock = threading.Lock()
        self._pressed_modifiers: Set[str] = set()
        self._backend: str = self._detect_backend()

        # Parse le hotkey initial
        self._hotkey_str = hotkey
        self._modifiers, self._main_key = parse_hotkey(hotkey)

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
        _init_pynput_maps()

        # Tracker les modifiers enfonces
        for mod_name, mod_keys in _PYNPUT_MODIFIER_MAP.items():
            if key in mod_keys:
                self._pressed_modifiers.add(mod_name)
                return

        # Verifier la main key
        target_key = self._resolve_pynput_key(self._main_key)
        if target_key is None:
            return

        if key != target_key:
            return

        # Verifier que tous les modifiers requis sont enfonces
        if not self._modifiers.issubset(self._pressed_modifiers):
            return

        self._handle_hotkey()

    def _on_release_pynput(self, key) -> None:
        """Callback pynput pour les relachements clavier."""
        _init_pynput_maps()
        for mod_name, mod_keys in _PYNPUT_MODIFIER_MAP.items():
            if key in mod_keys:
                self._pressed_modifiers.discard(mod_name)

    @staticmethod
    def _resolve_pynput_key(key_name: str) -> object:
        """Resout un nom de touche en objet pynput Key ou KeyCode.

        Args:
            key_name: Nom de la touche en minuscules (ex: "f8", "v", "space").

        Returns:
            Objet pynput Key/KeyCode ou None.
        """
        from pynput.keyboard import Key, KeyCode
        _init_pynput_maps()

        # Touches fonction
        if key_name in _PYNPUT_KEY_MAP:
            return _PYNPUT_KEY_MAP[key_name]

        # Touches speciales
        special_map = {
            "space": Key.space, "enter": Key.enter, "tab": Key.tab,
            "esc": Key.esc, "escape": Key.esc, "backspace": Key.backspace,
            "delete": Key.delete, "home": Key.home, "end": Key.end,
            "pageup": Key.page_up, "pagedown": Key.page_down,
            "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
            "insert": Key.insert,
        }
        if key_name in special_map:
            return special_map[key_name]

        # Lettre ou chiffre simple
        if len(key_name) == 1:
            return KeyCode.from_char(key_name)

        logger.warning(f"Touche inconnue: {key_name}")
        return None

    def _run_evdev(self) -> None:
        """Boucle de lecture evdev (tourne dans un thread daemon)."""
        import evdev
        from evdev import ecodes

        evdev_key_map = {}
        for i in range(1, 13):
            evdev_key_map[f"f{i}"] = getattr(ecodes, f"KEY_F{i}")
        # Lettres
        for c in "abcdefghijklmnopqrstuvwxyz":
            evdev_key_map[c] = getattr(ecodes, f"KEY_{c.upper()}")
        # Chiffres
        for d in "0123456789":
            evdev_key_map[d] = getattr(ecodes, f"KEY_{d}")
        evdev_key_map.update({
            "space": ecodes.KEY_SPACE, "enter": ecodes.KEY_ENTER,
            "tab": ecodes.KEY_TAB, "esc": ecodes.KEY_ESC,
            "escape": ecodes.KEY_ESC, "backspace": ecodes.KEY_BACKSPACE,
            "delete": ecodes.KEY_DELETE,
        })

        evdev_modifier_map = {
            "ctrl": {ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL},
            "shift": {ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT},
            "alt": {ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT},
            "super": {ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA},
            "cmd": {ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA},
        }

        target_code = evdev_key_map.get(self._main_key)
        if target_code is None:
            logger.error(f"Hotkey main key '{self._main_key}' non supportee avec evdev")
            return

        # Ensemble inverse : code -> nom modifier
        code_to_modifier: dict = {}
        for mod_name, codes in evdev_modifier_map.items():
            for code in codes:
                code_to_modifier[code] = mod_name

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

        evdev_pressed_mods: Set[str] = set()

        self._evdev_running = True
        while self._evdev_running:
            events = sel.select(timeout=0.5)
            for key_sel, mask in events:
                device = key_sel.fileobj
                try:
                    for event in device.read():
                        if event.type != ecodes.EV_KEY:
                            continue
                        # Tracker modifiers
                        mod_name = code_to_modifier.get(event.code)
                        if mod_name:
                            if event.value in (1, 2):  # press/repeat
                                evdev_pressed_mods.add(mod_name)
                            elif event.value == 0:  # release
                                evdev_pressed_mods.discard(mod_name)
                            continue
                        # Main key press
                        if event.value == 1 and event.code == target_code:
                            if self._modifiers.issubset(evdev_pressed_mods):
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

    def update_hotkey(self, new_hotkey: str) -> None:
        """Met a jour le hotkey a chaud sans redemarrer le listener.

        Args:
            new_hotkey: Nouvelle chaine hotkey (ex: "Ctrl+Shift+D").
        """
        modifiers, main_key = parse_hotkey(new_hotkey)
        self._hotkey_str = new_hotkey
        self._modifiers = modifiers
        self._main_key = main_key
        self._pressed_modifiers.clear()
        logger.info(f"Hotkey mis a jour: {new_hotkey}")

    @property
    def hotkey(self) -> str:
        """Retourne la chaine hotkey courante."""
        return self._hotkey_str

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
            self._listener = Listener(
                on_press=self._on_press_pynput,
                on_release=self._on_release_pynput,
            )
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
