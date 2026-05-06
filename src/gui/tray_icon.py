"""System tray icon pour VoxWave avec QSystemTrayIcon (PySide6)."""

import logging
import threading
import webbrowser
from typing import Callable, Optional

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from src import __version__
from src.gui.icons import IconState, create_qicon

logger = logging.getLogger(__name__)

_TRAY_T = {
    "en": {
        "start": "\u25b6  Start dictation",
        "stop": "\u25a0  Stop dictation",
        "settings": "\u2699  Settings",
        "help": "\u2753  Help",
        "license": "\u2727  Activate license",
        "about": "\u24d8  About",
        "quit": "\u2715  Quit",
        "tooltip": "VoxWave \u2014 Voice dictation",
        "update": "\u2b06  Update available (v{version})",
    },
    "fr": {
        "start": "\u25b6  Demarrer la dictee",
        "stop": "\u25a0  Arreter la dictee",
        "settings": "\u2699  Parametres",
        "help": "\u2753  Aide",
        "license": "\u2727  Activer licence",
        "about": "\u24d8  A propos",
        "quit": "\u2715  Quitter",
        "tooltip": "VoxWave \u2014 Dictee vocale",
        "update": "\u2b06  Mise a jour disponible (v{version})",
    },
    "es": {
        "start": "\u25b6  Iniciar dictado",
        "stop": "\u25a0  Detener dictado",
        "settings": "\u2699  Configuracion",
        "help": "\u2753  Ayuda",
        "license": "\u2727  Activar licencia",
        "about": "\u24d8  Acerca de",
        "quit": "\u2715  Salir",
        "tooltip": "VoxWave \u2014 Dictado por voz",
        "update": "\u2b06  Actualizacion disponible (v{version})",
    },
    "de": {
        "start": "\u25b6  Diktat starten",
        "stop": "\u25a0  Diktat stoppen",
        "settings": "\u2699  Einstellungen",
        "help": "\u2753  Hilfe",
        "license": "\u2727  Lizenz aktivieren",
        "about": "\u24d8  Uber",
        "quit": "\u2715  Beenden",
        "tooltip": "VoxWave \u2014 Sprachdiktat",
        "update": "\u2b06  Update verfugbar (v{version})",
    },
    "it": {
        "start": "\u25b6  Avvia dettatura",
        "stop": "\u25a0  Ferma dettatura",
        "settings": "\u2699  Impostazioni",
        "help": "\u2753  Aiuto",
        "license": "\u2727  Attiva licenza",
        "about": "\u24d8  Informazioni",
        "quit": "\u2715  Esci",
        "tooltip": "VoxWave \u2014 Dettatura vocale",
        "update": "\u2b06  Aggiornamento disponibile (v{version})",
    },
    "pt": {
        "start": "\u25b6  Iniciar ditado",
        "stop": "\u25a0  Parar ditado",
        "settings": "\u2699  Configuracoes",
        "help": "\u2753  Ajuda",
        "license": "\u2727  Ativar licenca",
        "about": "\u24d8  Sobre",
        "quit": "\u2715  Sair",
        "tooltip": "VoxWave \u2014 Ditado por voz",
        "update": "\u2b06  Atualizacao disponivel (v{version})",
    },
    "nl": {
        "start": "▶  Dicteren starten", "stop": "■  Dicteren stoppen",
        "settings": "⚙  Instellingen", "help": "❓  Help",
        "license": "✧  Licentie activeren", "about": "ⓘ  Over",
        "quit": "✕  Afsluiten", "tooltip": "VoxWave — Spraakdictaat",
        "update": "⬆  Update beschikbaar (v{version})",
    },
    "ja": {
        "start": "▶  ディクテーション開始", "stop": "■  ディクテーション停止",
        "settings": "⚙  設定", "help": "❓  ヘルプ",
        "license": "✧  ライセンスを有効化", "about": "ⓘ  概要",
        "quit": "✕  終了", "tooltip": "VoxWave — 音声ディクテーション",
        "update": "⬆  アップデートあり (v{version})",
    },
    "ko": {
        "start": "▶  받아쓰기 시작", "stop": "■  받아쓰기 중지",
        "settings": "⚙  설정", "help": "❓  도움말",
        "license": "✧  라이선스 활성화", "about": "ⓘ  정보",
        "quit": "✕  종료", "tooltip": "VoxWave — 음성 받아쓰기",
        "update": "⬆  업데이트 가능 (v{version})",
    },
    "zh": {
        "start": "▶  开始听写", "stop": "■  停止听写",
        "settings": "⚙  设置", "help": "❓  帮助",
        "license": "✧  激活许可证", "about": "ⓘ  关于",
        "quit": "✕  退出", "tooltip": "VoxWave — 语音听写",
        "update": "⬆  有更新 (v{version})",
    },
    "ru": {
        "start": "▶  Nachat diktovku", "stop": "■  Ostanovit diktovku",
        "settings": "⚙  Nastrojki", "help": "❓  Pomosh",
        "license": "✧  Aktivirovat licenziju", "about": "ⓘ  O programme",
        "quit": "✕  Vyjti", "tooltip": "VoxWave — Golosovaja diktovka",
        "update": "⬆  Dostupno obnovlenie (v{version})",
    },
    "ar": {
        "start": "▶  بدء الإملاء", "stop": "■  إيقاف الإملاء",
        "settings": "⚙  الإعدادات", "help": "❓  مساعدة",
        "license": "✧  تفعيل الترخيص", "about": "ⓘ  حول",
        "quit": "✕  خروج", "tooltip": "VoxWave — الإملاء الصوتي",
        "update": "⬆  تحديث متاح (v{version})",
    },
    "tr": {
        "start": "▶  Dikteyi baslat", "stop": "■  Dikteyi durdur",
        "settings": "⚙  Ayarlar", "help": "❓  Yardim",
        "license": "✧  Lisansi etkinlestir", "about": "ⓘ  Hakkinda",
        "quit": "✕  Cikis", "tooltip": "VoxWave — Sesli dikte",
        "update": "⬆  Guncelleme mevcut (v{version})",
    },
    "pl": {
        "start": "▶  Rozpocznij dyktowanie", "stop": "■  Zatrzymaj dyktowanie",
        "settings": "⚙  Ustawienia", "help": "❓  Pomoc",
        "license": "✧  Aktywuj licencje", "about": "ⓘ  O programie",
        "quit": "✕  Wyjdz", "tooltip": "VoxWave — Dyktowanie glosowe",
        "update": "⬆  Aktualizacja dostepna (v{version})",
    },
    "sv": {
        "start": "▶  Starta diktering", "stop": "■  Stoppa diktering",
        "settings": "⚙  Installningar", "help": "❓  Hjalp",
        "license": "✧  Aktivera licens", "about": "ⓘ  Om",
        "quit": "✕  Avsluta", "tooltip": "VoxWave — Rostdiktering",
        "update": "⬆  Uppdatering tillganglig (v{version})",
    },
}


def _tt(lang: str, key: str) -> str:
    d = _TRAY_T.get(lang, _TRAY_T["en"])
    return d.get(key, _TRAY_T["en"][key])


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
        language: str = "en",
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
            language: Code langue de l'interface (ex: "fr", "en").
        """
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_quit = on_quit
        self.on_activate_license = on_activate_license
        self.on_settings = on_settings
        self.on_help = on_help
        self.on_tray_clicked = on_tray_clicked
        self._language = language
        self._state: IconState = "idle"
        self._is_recording = False
        self._tray: Optional[QSystemTrayIcon] = None
        self._menu: Optional[QMenu] = None
        self._start_action: Optional[QAction] = None
        self._stop_action: Optional[QAction] = None
        self._settings_action: Optional[QAction] = None
        self._help_action: Optional[QAction] = None
        self._license_action: Optional[QAction] = None
        self._about_action: Optional[QAction] = None
        self._quit_action: Optional[QAction] = None
        self._update_action: Optional[QAction] = None
        self._update_version: Optional[str] = None

    def _create_menu(self) -> QMenu:
        """Cree le menu contextuel du tray."""
        menu = QMenu()

        # --- Groupe enregistrement ---
        self._start_action = QAction(_tt(self._language, "start"), menu)
        self._start_action.triggered.connect(self._toggle_start)
        menu.addAction(self._start_action)

        self._stop_action = QAction(_tt(self._language, "stop"), menu)
        self._stop_action.triggered.connect(self._toggle_stop)
        self._stop_action.setVisible(False)
        menu.addAction(self._stop_action)

        menu.addSeparator()

        # --- Groupe parametres ---
        self._settings_action = QAction(_tt(self._language, "settings"), menu)
        self._settings_action.triggered.connect(self._on_settings_click)
        menu.addAction(self._settings_action)

        self._help_action = QAction(_tt(self._language, "help"), menu)
        self._help_action.triggered.connect(self._on_help_click)
        menu.addAction(self._help_action)

        menu.addSeparator()

        # --- Groupe licence / about ---
        self._license_action = QAction(_tt(self._language, "license"), menu)
        self._license_action.triggered.connect(self._on_activate_license_click)
        menu.addAction(self._license_action)

        self._about_action = QAction(_tt(self._language, "about"), menu)
        self._about_action.triggered.connect(self._on_about)
        menu.addAction(self._about_action)

        menu.addSeparator()

        # --- Quitter ---
        self._quit_action = QAction(_tt(self._language, "quit"), menu)
        self._quit_action.triggered.connect(self._on_quit_click)
        menu.addAction(self._quit_action)

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
        """Affiche les infos sur VoxWave."""
        self.show_notification("VoxWave", f"VoxWave v{__version__} — Dictee vocale intelligente")

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

    def add_update_action(self, version: str, download_url: str) -> None:
        """Ajoute une action 'Mise à jour disponible' dans le menu tray.

        Insérée juste avant le séparateur Quitter. Si déjà présente, met à jour le texte.

        Args:
            version: Nouvelle version disponible (ex: "1.2.0").
            download_url: URL directe vers le fichier à télécharger.
        """
        if not self._menu:
            return

        self._update_version = version
        text = _tt(self._language, "update").format(version=version)

        if self._update_action:
            self._update_action.setText(text)
            return

        self._update_action = QAction(text, self._menu)
        self._update_action.triggered.connect(
            lambda: webbrowser.open(download_url)
        )

        # Insérer avant la dernière action (Quitter)
        if self._quit_action:
            self._menu.insertAction(self._quit_action, self._update_action)
            self._menu.insertSeparator(self._quit_action)

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
        self._tray.setToolTip(_tt(self._language, "tooltip"))
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()
        logger.info("System tray demarre (QSystemTrayIcon)")

    def update_language(self, lang: str) -> None:
        """Met a jour la langue du menu tray (hot-reload sans redemarrage).

        Args:
            lang: Nouveau code langue (ex: "fr", "en").
        """
        self._language = lang
        if self._start_action:
            self._start_action.setText(_tt(lang, "start"))
        if self._stop_action:
            self._stop_action.setText(_tt(lang, "stop"))
        if self._settings_action:
            self._settings_action.setText(_tt(lang, "settings"))
        if self._help_action:
            self._help_action.setText(_tt(lang, "help"))
        if self._license_action:
            self._license_action.setText(_tt(lang, "license"))
        if self._about_action:
            self._about_action.setText(_tt(lang, "about"))
        if self._quit_action:
            self._quit_action.setText(_tt(lang, "quit"))
        if self._update_action and self._update_version:
            self._update_action.setText(
                _tt(lang, "update").format(version=self._update_version)
            )
        if self._tray:
            self._tray.setToolTip(_tt(lang, "tooltip"))

    def run(self) -> None:
        """Lance le tray icon (pour compatibilite — appelle setup)."""
        self.setup()

    def run_detached(self) -> None:
        """Lance le tray icon (pour compatibilite — appelle setup)."""
        self.setup()

    def reshow(self) -> None:
        """Recree le tray icon (apres restart Explorer ou panel Linux).

        Qt garde un handle Windows interne invalide apres Explorer restart
        (QTBUG-29160). Seule la recreation force un nouveau slot dans la
        notification area.
        """
        if self._tray:
            self._tray.hide()
            self._tray.deleteLater()
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(create_qicon(self._state))
        self._tray.setToolTip(_tt(self._language, "tooltip"))
        if self._menu:
            self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()
        logger.info("System tray recree (reshow)")

    def stop(self) -> None:
        """Arrete le tray icon."""
        if self._tray:
            self._tray.hide()
            self._tray = None
