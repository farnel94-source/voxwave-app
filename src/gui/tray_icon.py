"""System tray icon pour The Wave avec QSystemTrayIcon (PySide6)."""

import logging
import threading
from typing import Callable, Optional

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from src.gui.icons import IconState, create_qicon

logger = logging.getLogger(__name__)


class TrayIcon:
    """Icone system tray avec menu contextuel (PySide6)."""

    def __init__(
        self,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
        on_activate_license: Optional[Callable] = None,
        on_settings: Optional[Callable] = None,
        on_help: Optional[Callable] = None,
        on_tray_clicked: Optional[Callable] = None,
    ) -> None:
        """Initialise le tray icon.

        Args:
            on_start: Callback pour demarrer l'enregistrement.
            on_stop: Callback pour arreter l'enregistrement.
            on_quit: Callback pour quitter l'application.
            on_activate_license: Callback pour activer la licence.
            on_settings: Callback pour ouvrir les parametres.
            on_help: Callback pour ouvrir l'aide (settings onglet Aide).
            on_tray_clicked: Callback quand l'icone tray est cliquee (clic simple).
        """
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_quit = on_quit
        self.on_activate_license = on_activate_license
        self.on_settings = on_settings
        self.on_help = on_help
        self.on_tray_clicked = on_tray_clicked
        self._state: IconState = "idle"
        self._is_recording = False
        self._tray: Optional[QSystemTrayIcon] = None
        self._menu: Optional[QMenu] = None
        self._start_action: Optional[QAction] = None
        self._stop_action: Optional[QAction] = None

    def _create_menu(self) -> QMenu:
        """Cree le menu contextuel du tray."""
        menu = QMenu()

        # --- Groupe enregistrement ---
        self._start_action = QAction("\u25b6  Demarrer la dictee", menu)
        self._start_action.triggered.connect(self._toggle_start)
        menu.addAction(self._start_action)

        self._stop_action = QAction("\u25a0  Arreter la dictee", menu)
        self._stop_action.triggered.connect(self._toggle_stop)
        self._stop_action.setVisible(False)
        menu.addAction(self._stop_action)

        menu.addSeparator()

        # --- Groupe parametres ---
        settings_action = QAction("\u2699  Parametres", menu)
        settings_action.triggered.connect(self._on_settings_click)
        menu.addAction(settings_action)

        help_action = QAction("\u2753  Aide", menu)
        help_action.triggered.connect(self._on_help_click)
        menu.addAction(help_action)

        menu.addSeparator()

        # --- Groupe licence / about ---
        license_action = QAction("\u2727  Activer licence", menu)
        license_action.triggered.connect(self._on_activate_license_click)
        menu.addAction(license_action)

        about_action = QAction("\u24d8  A propos", menu)
        about_action.triggered.connect(self._on_about)
        menu.addAction(about_action)

        menu.addSeparator()

        # --- Quitter ---
        quit_action = QAction("\u2715  Quitter", menu)
        quit_action.triggered.connect(self._on_quit_click)
        menu.addAction(quit_action)

        return menu

    def _toggle_start(self) -> None:
        """Demarre l'enregistrement via le menu tray."""
        self._is_recording = True
        self._update_menu_visibility()
        if self.on_start:
            self.on_start()

    def _toggle_stop(self) -> None:
        """Arrete l'enregistrement via le menu tray."""
        self._is_recording = False
        self._update_menu_visibility()
        if self.on_stop:
            self.on_stop()

    def _update_menu_visibility(self) -> None:
        """Met a jour la visibilite des items du menu."""
        if self._start_action:
            self._start_action.setVisible(not self._is_recording)
        if self._stop_action:
            self._stop_action.setVisible(self._is_recording)

    def _on_settings_click(self) -> None:
        """Ouvre le dialogue des parametres."""
        if self.on_settings:
            self.on_settings()

    def _on_activate_license_click(self) -> None:
        """Ouvre le dialog de licence."""
        if self.on_activate_license:
            thread = threading.Thread(target=self.on_activate_license, daemon=True)
            thread.start()

    def _on_help_click(self) -> None:
        """Ouvre l'aide (settings sur l'onglet Aide)."""
        if self.on_help:
            self.on_help()

    def _on_about(self) -> None:
        """Affiche les infos sur The Wave."""
        self.show_notification("The Wave", "The Wave v2.1 — Dictee vocale intelligente")

    def _on_quit_click(self) -> None:
        """Quitte l'application."""
        logger.info("Quit demande via tray")
        if self.on_quit:
            self.on_quit()
        self.stop()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Gere le clic sur l'icone tray.

        Args:
            reason: Raison de l'activation (clic simple, double-clic, etc.).
        """
        # Trigger = clic simple (gauche)
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.on_tray_clicked:
                self.on_tray_clicked()

    def set_state(self, state: IconState) -> None:
        """Change l'etat visuel de l'icone.

        Args:
            state: Nouvel etat (idle, recording, processing, error).
        """
        self._state = state
        if state == "recording":
            self._is_recording = True
        elif state == "idle":
            self._is_recording = False

        self._update_menu_visibility()
        if self._tray:
            self._tray.setIcon(create_qicon(state))

    def show_notification(self, title: str, message: str) -> None:
        """Affiche une notification OS.

        Args:
            title: Titre de la notification.
            message: Message de la notification.
        """
        if self._tray and QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(title, message, create_qicon(self._state), 3000)

    def setup(self) -> None:
        """Cree et configure le tray icon (doit etre appele apres QApplication)."""
        self._menu = self._create_menu()
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(create_qicon("idle"))
        self._tray.setToolTip("The Wave — Dictee vocale")
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()
        logger.info("System tray demarre (QSystemTrayIcon)")

    def run(self) -> None:
        """Lance le tray icon (pour compatibilite — appelle setup)."""
        self.setup()

    def run_detached(self) -> None:
        """Lance le tray icon (pour compatibilite — appelle setup)."""
        self.setup()

    def stop(self) -> None:
        """Arrete le tray icon."""
        if self._tray:
            self._tray.hide()
            self._tray = None
