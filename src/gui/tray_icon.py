"""System tray icon pour VoxTool avec pystray."""

import logging
import threading
from typing import Callable, Optional

import pystray
from pystray import MenuItem as Item

from src.gui.icons import IconState, create_icon

logger = logging.getLogger(__name__)


class TrayIcon:
    """Icône system tray avec menu contextuel."""

    def __init__(
        self,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
        on_activate_license: Optional[Callable] = None,
    ) -> None:
        """Initialise le tray icon.

        Args:
            on_start: Callback pour démarrer l'enregistrement.
            on_stop: Callback pour arrêter l'enregistrement.
            on_quit: Callback pour quitter l'application.
            on_activate_license: Callback pour activer la licence.
        """
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_quit = on_quit
        self.on_activate_license = on_activate_license
        self._state: IconState = "idle"
        self._is_recording = False
        self._icon: Optional[pystray.Icon] = None
        self._lock = threading.Lock()

    def _create_menu(self) -> pystray.Menu:
        """Crée le menu contextuel du tray."""
        return pystray.Menu(
            Item(
                "Démarrer l'enregistrement",
                self._toggle_recording,
                visible=lambda item: not self._is_recording,
            ),
            Item(
                "Arrêter l'enregistrement",
                self._toggle_recording,
                visible=lambda item: self._is_recording,
            ),
            pystray.Menu.SEPARATOR,
            Item("Activer licence...", self._on_activate_license_click),
            Item("À propos", self._on_about),
            pystray.Menu.SEPARATOR,
            Item("Quitter", self._on_quit_click),
        )

    def _toggle_recording(self, icon, item) -> None:
        """Toggle enregistrement via le menu tray."""
        if self._is_recording:
            self._is_recording = False
            if self.on_stop:
                self.on_stop()
        else:
            self._is_recording = True
            if self.on_start:
                self.on_start()

    def _on_activate_license_click(self, icon, item) -> None:
        """Ouvre le dialog de licence."""
        if self.on_activate_license:
            thread = threading.Thread(target=self.on_activate_license, daemon=True)
            thread.start()

    def _on_about(self, icon, item) -> None:
        """Affiche les infos sur VoxTool."""
        self.show_notification("VoxTool", "VoxTool v1.0 — Dictée vocale intelligente")

    def _on_quit_click(self, icon, item) -> None:
        """Quitte l'application."""
        logger.info("Quit demandé via tray")
        if self.on_quit:
            self.on_quit()
        self.stop()

    def set_state(self, state: IconState) -> None:
        """Change l'état visuel de l'icône.

        Args:
            state: Nouvel état (idle, recording, processing, error).
        """
        with self._lock:
            self._state = state
            if state == "recording":
                self._is_recording = True
            elif state == "idle":
                self._is_recording = False

            if self._icon:
                self._icon.icon = create_icon(state)
                self._icon.update_menu()

    def show_notification(self, title: str, message: str) -> None:
        """Affiche une notification OS.

        Args:
            title: Titre de la notification.
            message: Message de la notification.
        """
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception as e:
                logger.debug(f"Notification échouée: {e}")

    def run(self) -> None:
        """Lance le tray icon (bloquant)."""
        self._icon = self._create_pystray_icon()
        logger.info("System tray démarré (bloquant)")
        self._icon.run()

    def run_detached(self) -> None:
        """Lance le tray icon en mode non-bloquant (thread séparé)."""
        self._icon = self._create_pystray_icon()
        self._icon.run_detached()
        logger.info("System tray démarré (détaché)")

    def _create_pystray_icon(self) -> pystray.Icon:
        """Crée l'instance pystray.Icon."""
        return pystray.Icon(
            "VoxTool",
            icon=create_icon("idle"),
            title="VoxTool — Dictée vocale",
            menu=self._create_menu(),
        )

    def stop(self) -> None:
        """Arrête le tray icon."""
        if self._icon:
            self._icon.stop()
            self._icon = None
