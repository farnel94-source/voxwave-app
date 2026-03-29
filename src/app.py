"""VoxWave — Point d'entree principal.

Usage:
    python -m voxwave
    python -m voxwave --model small
    python -m voxwave --test
"""

import logging
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

# Fix encodage Unicode sur Windows (emojis dans le terminal)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import click
import sentry_sdk
import yaml
from dotenv import load_dotenv

from src.utils.platform import resource_path
from src.transcription.hallucinations import is_hallucination, strip_hallucination_tails
from src.utils.window_detector import get_active_exe, get_app_profile

load_dotenv(resource_path(".env"))

# --- Sentry : crash reporting automatique ---
# Envoie les erreurs non-catchées à Sentry pour qu'on voie les bugs
# des utilisateurs sans qu'ils aient besoin de faire quoi que ce soit.
# Le DSN est dans .env — si absent, Sentry est simplement désactivé (pas de crash).
from src import __version__

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN", ""),
    release=f"voxwave@{__version__}",
    traces_sample_rate=0.1,  # 10% des transactions pour le monitoring de perf
    environment="production",
)

logger = logging.getLogger(__name__)

_APP_STEP_T = {
    "en": {"transcription": "Transcription...", "cleaning": "Cleaning...", "injection": "Injecting...", "processing": "Processing..."},
    "fr": {"transcription": "Transcription...", "cleaning": "Nettoyage...", "injection": "Injection...", "processing": "Traitement..."},
    "es": {"transcription": "Transcripcion...", "cleaning": "Limpieza...", "injection": "Inyectando...", "processing": "Procesando..."},
    "de": {"transcription": "Transkription...", "cleaning": "Bereinigung...", "injection": "Einfuegen...", "processing": "Verarbeitung..."},
    "it": {"transcription": "Trascrizione...", "cleaning": "Pulizia...", "injection": "Inserimento...", "processing": "Elaborazione..."},
    "pt": {"transcription": "Transcricao...", "cleaning": "Limpeza...", "injection": "Injecao...", "processing": "Processando..."},
    "nl": {"transcription": "Transcriptie...", "cleaning": "Verwerking...", "injection": "Invoegen...", "processing": "Bezig..."},
    "ja": {"transcription": "文字起こし...", "cleaning": "整理中...", "injection": "貼り付け中...", "processing": "処理中..."},
    "ko": {"transcription": "전사 중...", "cleaning": "정리 중...", "injection": "입력 중...", "processing": "처리 중..."},
    "zh": {"transcription": "转录中...", "cleaning": "整理中...", "injection": "粘贴中...", "processing": "处理中..."},
    "ru": {"transcription": "Transkriptsija...", "cleaning": "Obrabotka...", "injection": "Vstavka...", "processing": "Obrabotka..."},
    "ar": {"transcription": "نسخ...", "cleaning": "تنظيف...", "injection": "لصق...", "processing": "معالجة..."},
    "tr": {"transcription": "Transkripsiyon...", "cleaning": "Temizleniyor...", "injection": "Yapistiriliyor...", "processing": "Isleniyor..."},
    "pl": {"transcription": "Transkrypcja...", "cleaning": "Czyszczenie...", "injection": "Wklejanie...", "processing": "Przetwarzanie..."},
    "sv": {"transcription": "Transkription...", "cleaning": "Rensning...", "injection": "Inklistring...", "processing": "Bearbetar..."},
}

_ERROR_T = {
    "en": "Error", "fr": "Erreur", "es": "Error", "de": "Fehler", "it": "Errore", "pt": "Erro",
    "nl": "Fout", "ja": "エラー", "ko": "오류", "zh": "错误",
    "ru": "Oshibka", "ar": "خطأ", "tr": "Hata", "pl": "Blad", "sv": "Fel",
}

_BUSY_T = {
    "en": "Processing in progress, please wait...",
    "fr": "Traitement en cours, veuillez patienter...",
    "es": "Procesando, por favor espere...",
    "de": "Verarbeitung läuft, bitte warten...",
    "it": "Elaborazione in corso, attendere...",
    "pt": "Processando, aguarde...",
    "nl": "Bezig met verwerken, even geduld...",
    "ja": "処理中です、お待ちください...",
    "ko": "처리 중입니다, 잠시 기다려주세요...",
    "zh": "正在处理，请稍候...",
    "ru": "Obrabotka, podozhdite...",
    "ar": "جارٍ المعالجة، يرجى الانتظار...",
    "tr": "İşleniyor, lütfen bekleyin...",
    "pl": "Przetwarzanie, proszę czekać...",
    "sv": "Bearbetar, vänta...",
}

_UPDATE_NOTIF_T = {
    "en": "VoxWave v{version} is available! Click the tray menu to download.",
    "fr": "VoxWave v{version} est disponible ! Cliquez dans le menu tray pour telecharger.",
    "es": "VoxWave v{version} esta disponible! Haga clic en el menu de bandeja para descargar.",
    "de": "VoxWave v{version} ist verfugbar! Klicken Sie im Tray-Menu zum Herunterladen.",
    "it": "VoxWave v{version} e disponibile! Clicca nel menu tray per scaricare.",
    "pt": "VoxWave v{version} esta disponivel! Clique no menu da bandeja para baixar.",
    "nl": "VoxWave v{version} is beschikbaar! Klik in het tray-menu om te downloaden.",
    "ja": "VoxWave v{version} が利用可能です！トレイメニューからダウンロードしてください。",
    "ko": "VoxWave v{version} 사용 가능! 트레이 메뉴에서 다운로드하세요.",
    "zh": "VoxWave v{version} 可用！点击托盘菜单下载。",
    "ru": "VoxWave v{version} dostupna! Nazhmite v tray-menu dlja zagruzki.",
    "ar": "VoxWave v{version} متاح! انقر على قائمة العلبة للتنزيل.",
    "tr": "VoxWave v{version} mevcut! Indirmek icin tepsi menusune tiklayin.",
    "pl": "VoxWave v{version} jest dostepny! Kliknij w menu zasobnika, aby pobrac.",
    "sv": "VoxWave v{version} ar tillganglig! Klicka i tray-menyn for att ladda ner.",
}


def _app_t(lang: str, key: str) -> str:
    d = _APP_STEP_T.get(lang, _APP_STEP_T["en"])
    return d.get(key, _APP_STEP_T["en"][key])


def _get_log_dir() -> str:
    """Retourne le dossier de logs (~/.voxwave/logs/)."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, "VoxWave", "logs")
    return os.path.join(os.path.expanduser("~"), ".voxwave", "logs")


def setup_logging(level: str = "INFO") -> None:
    from logging.handlers import RotatingFileHandler

    log_dir = _get_log_dir()
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "voxwave.log")

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            # 5 Mo max par fichier, garde les 3 derniers (= 15 Mo max total)
            RotatingFileHandler(
                log_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
            ),
        ]
    )
    logging.getLogger(__name__).info(f"Logs: {log_file}")


def load_config(config_path: str = "config.yaml") -> dict:
    """Charge et valide la configuration.

    Args:
        config_path: Chemin vers config.yaml.

    Returns:
        Configuration validee et completee avec les defauts.
    """
    from src.config.validator import ConfigValidator
    from src.config.defaults import DEFAULT_CONFIG
    from src.utils.platform import user_config_path

    # En mode frozen, utilise le config utilisateur (~/.config/voxwave/)
    resolved_path = user_config_path()

    try:
        with open(resolved_path, "r") as f:
            user_config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"Config {config_path} introuvable, utilisation des defauts")
        user_config = {}
    except yaml.YAMLError as e:
        logger.error(f"Erreur parsing config: {e}, utilisation des defauts")
        user_config = {}

    return ConfigValidator.validate_and_merge(user_config)


class _TaskbarWindow:
    """Fenetre fantome pour donner a l'app une presence dans la barre des taches Windows.

    Affichee comme minimisee (invisible) mais visible dans la barre des taches avec
    le logo VoxWave. Clic sur l'icone -> ouvre les Parametres.
    """

    def __init__(self, on_activate, app_icon, on_taskbar_created=None) -> None:
        from PySide6.QtCore import QEvent, Qt, QTimer
        from PySide6.QtWidgets import QWidget

        # Enregistrer le message Windows broadcast "TaskbarCreated"
        # (envoye par Explorer quand il redemarre)
        taskbar_created_msg = None
        if sys.platform == "win32" and on_taskbar_created:
            import ctypes
            taskbar_created_msg = ctypes.windll.user32.RegisterWindowMessageW("TaskbarCreated")
            logger.debug("TaskbarCreated message enregistre: %s", taskbar_created_msg)

        class _Anchor(QWidget):
            def nativeEvent(self_, event_type, message):  # noqa: N805
                """Windows: intercepte WM_SYSCOMMAND SC_RESTORE (clic barre des taches).

                Consume le message pour empecher la fenetre de se restaurer (pas de flash).
                Appele exactement une fois par clic utilisateur.
                Ecoute aussi TaskbarCreated pour recreer le tray icon apres restart Explorer.
                """
                if event_type == b"windows_generic_MSG":
                    import ctypes

                    class _MSG(ctypes.Structure):
                        _fields_ = [
                            ("hWnd", ctypes.c_size_t),
                            ("message", ctypes.c_uint),
                            ("wParam", ctypes.c_size_t),
                            ("lParam", ctypes.c_ssize_t),
                        ]

                    msg = _MSG.from_address(int(message))

                    # TaskbarCreated : Explorer a redemarre, recreer le tray icon
                    if taskbar_created_msg and msg.message == taskbar_created_msg:
                        logger.info("TaskbarCreated recu — Explorer a redemarre")
                        QTimer.singleShot(500, on_taskbar_created)
                        # Ne pas consumer — laisser Qt traiter aussi

                    WM_SYSCOMMAND = 0x0112
                    SC_RESTORE = 0xF120
                    if msg.message == WM_SYSCOMMAND and (msg.wParam & 0xFFF0) == SC_RESTORE:
                        print("[TaskbarWindow] SC_RESTORE intercepte -> ouverture Settings", flush=True)
                        # Differe d'un tick : nativeEvent retourne d'abord True,0 →
                        # Windows met a jour son etat interne → GetForegroundWindow()
                        # retourne la VRAIE fenetre active quand on_activate s'execute.
                        QTimer.singleShot(0, on_activate)
                        return True, 0  # Consomme le message : fenetre reste minimisee
                return super(_Anchor, self_).nativeEvent(event_type, message)

            def changeEvent(self_, event) -> None:  # noqa: N805
                """Securite : re-minimise si la fenetre se retrouve visible (Linux ou cas edge)."""
                if event.type() == QEvent.Type.WindowStateChange:
                    if not (self_.windowState() & Qt.WindowState.WindowMinimized):
                        self_.showMinimized()
                        if sys.platform != "win32":
                            on_activate()
                super(_Anchor, self_).changeEvent(event)

            def closeEvent(self_, event) -> None:  # noqa: N805
                event.ignore()
                self_.showMinimized()

        self._win = _Anchor()
        self._win.setWindowTitle("VoxWave")
        self._win.setWindowIcon(app_icon)
        self._win.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._win.setWindowOpacity(0.0)
        self._win.showMinimized()

        if sys.platform == "win32":
            from src.gui.icons import force_taskbar_icon_win32
            hwnd = int(self._win.winId())
            print(f"[TaskbarWindow] HWND = {hwnd}", flush=True)
            # Differement 300ms : l'Explorateur Windows cree le bouton barre des taches
            # de maniere asynchrone. On attend qu'il soit pret avant d'envoyer WM_SETICON.
            QTimer.singleShot(300, lambda: force_taskbar_icon_win32(hwnd))


class _HotkeyBridge:
    """Dispatcher thread-safe pour les callbacks hotkey.

    Le listener pynput tourne dans un thread arrière-plan. Ce bridge utilise
    les Qt signals pour dispatcher les callbacks vers le thread Qt principal,
    ce qui rend tous les appels GUI (tray, waveform) thread-safe.
    """

    def __init__(self) -> None:
        from PySide6.QtCore import QObject, Signal

        class _Bridge(QObject):
            sig_start = Signal()
            sig_stop = Signal()
            sig_busy = Signal()

        self._bridge = _Bridge()
        self.sig_start = self._bridge.sig_start
        self.sig_stop = self._bridge.sig_stop
        self.sig_busy = self._bridge.sig_busy


class _PipelineBridge:
    """Dispatcher thread-safe pour les appels tray depuis les threads pipeline.

    Les méthodes _process_audio et _process_audio_progressive tournent dans
    des threads secondaires. Ce bridge utilise les Qt signals pour dispatcher
    les appels tray.set_state() et tray.show_notification() vers le thread
    Qt principal (obligatoire pour les opérations GUI Qt).
    """

    def __init__(self) -> None:
        from PySide6.QtCore import QObject, Signal

        class _Bridge(QObject):
            sig_tray_set_state = Signal(str)
            sig_tray_notify = Signal(str, str)
            sig_update_available = Signal(str, str)

        self._bridge = _Bridge()
        self.sig_tray_set_state = self._bridge.sig_tray_set_state
        self.sig_tray_notify = self._bridge.sig_tray_notify
        self.sig_update_available = self._bridge.sig_update_available


def _force_foreground_win32(widget: "QWidget") -> None:
    """Force une fenetre au premier plan sur Windows.

    1. AttachThreadInput — attache notre thread a celui de la fenetre active
       pour obtenir le droit d'appeler SetForegroundWindow
    2. ShowWindow(SW_RESTORE) + BringWindowToTop + SetForegroundWindow
       pour restaurer et forcer la fenetre en avant-plan
    3. SetWindowPos TOPMOST → NOTOPMOST — filet de securite
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = int(widget.winId())
        user32 = ctypes.windll.user32

        # 1) AttachThreadInput : voler le droit de focus
        foreground_hwnd = user32.GetForegroundWindow()
        foreground_tid = user32.GetWindowThreadProcessId(foreground_hwnd, None)
        our_tid = user32.GetWindowThreadProcessId(hwnd, None)
        attached = False
        if foreground_tid != our_tid:
            attached = bool(user32.AttachThreadInput(foreground_tid, our_tid, True))

        # 2) Restaurer puis amener au premier plan
        SW_RESTORE = 9
        show_ret = user32.ShowWindow(hwnd, SW_RESTORE)
        bring_ret = user32.BringWindowToTop(hwnd)
        set_fg_ret = user32.SetForegroundWindow(hwnd)

        # 3) TOPMOST → NOTOPMOST en filet de securite
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, flags)   # HWND_TOPMOST
        user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, flags)   # HWND_NOTOPMOST

        logger.debug(
            "win32 focus: hwnd=%s attached=%s ShowWindow=%s BringWindowToTop=%s SetForegroundWindow=%s",
            hwnd,
            attached,
            show_ret,
            bring_ret,
            set_fg_ret,
        )

        # 4) Detacher les threads
        if attached:
            user32.AttachThreadInput(foreground_tid, our_tid, False)
    except Exception as e:
        logger.debug(f"win32 focus echec: {e}")


class VoxWave:
    """Application principale VoxWave."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.capture = None
        self.engine = None
        self.pipeline = None
        self.injector = None
        self.listener = None
        self.feedback = None
        self.tray = None
        self.waveform = None
        self.license_validator = None
        self._qt_app = None
        self._shutting_down = False
        self._stop_event = threading.Event()
        self._auto_stop_event = threading.Event()
        self._current_app_profile: str = "default"
        self._processing_thread: Optional[threading.Thread] = None
        self._processing_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._settings_dialog = None
        self._silero_vad = None
        self._prog_injector = None
        self._hotkey_bridge = None

    def initialize(self) -> None:
        """Initialise tous les composants."""
        from src.audio.capture import AudioCapture
        from src.audio.feedback import AudioFeedback
        from src.audio.processor import AudioProcessor
        from src.cleaning.llm_cleaner import CleaningPipeline
        from src.injection.keyboard import TextInjector
        from src.hotkey.listener import HotkeyListener

        logger.info("Initialisation VoxWave...")

        # Audio feedback
        feedback_config = self.config.get("audio", {}).get("feedback", {})
        self.feedback = AudioFeedback(
            enabled=feedback_config.get("enabled", True),
            volume=feedback_config.get("volume", 0.5),
        )

        # Valider le device_id si specifie
        from src.audio.device_manager import AudioDeviceManager
        device_id = self.config["audio"].get("device_id")
        device_id = AudioDeviceManager.validate_device(device_id)

        # Silero VAD : chargé en amont pour l'auto-stop (évite le délai au premier enregistrement)
        perf_config = self.config.get("performance", {})
        perf_mode = perf_config.get("mode", "both")
        silence_threshold_ms = perf_config.get("auto_stop_silence_ms", 500)

        if perf_mode in ("auto_stop", "both"):
            from src.audio.silero_vad import SileroVAD
            self._silero_vad = SileroVAD(threshold=0.5)
            logger.info(f"Silero VAD chargé (mode={perf_mode}, silence={silence_threshold_ms}ms)")

        self.capture = AudioCapture(
            sample_rate=self.config["audio"]["sample_rate"],
            channels=self.config["audio"]["channels"],
            chunk_size=self.config["audio"]["chunk_size"],
            silence_threshold=self.config["audio"]["silence_threshold"],
            device_id=device_id,
            silero_vad=self._silero_vad,
            on_silence_detected=self._schedule_auto_stop if self._silero_vad else None,
            silence_threshold_ms=silence_threshold_ms,
            on_auto_stop=self._schedule_auto_stop,
            auto_stop_enabled=self.config["audio"].get("auto_stop_enabled", False),
            auto_stop_silence_duration=self.config["audio"].get("auto_stop_silence_duration", 2.0),
        )
        vad_aggressiveness = self.config.get("audio", {}).get("vad_aggressiveness", 2)
        self.processor = AudioProcessor(
            sample_rate=self.config["audio"]["sample_rate"],
            vad_aggressiveness=vad_aggressiveness,
        )

        # Choix du moteur de transcription
        transcription_provider = self.config.get("transcription", {}).get("provider", "local")
        self.engine = self._create_transcription_engine(transcription_provider)

        # Auto-détecter l'hôte Ollama au démarrage
        detected_host = self._detect_ollama_host()
        self.config.setdefault("cleaning", {})["ollama_host"] = detected_host

        # Choix du pipeline de nettoyage
        cleaning_config = self.config.get("cleaning", {})  # re-read after detection
        cleaning_provider = cleaning_config.get("provider", "local")
        cloud_model = cleaning_config.get("cloud_model", "gpt-4o-mini")
        filler_words = cleaning_config.get("filler_words")
        self.pipeline = CleaningPipeline(
            mode=cleaning_config["mode"],
            llm_model=cleaning_config["llm_model"],
            cloud_model=cloud_model,
            cleaning_provider=cleaning_provider,
            language=self.config["whisper"]["language"],
            filler_words=filler_words,
            ollama_host=cleaning_config.get("ollama_host", "http://localhost:11434"),
            on_fallback=self._on_fallback,
        )

        # Informer si mode auto actif sans clé OpenAI disponible
        if cleaning_config.get("mode", "auto") != "raw":
            cloud_cleaner = getattr(self.pipeline, "_cloud_cleaner", None)
            if cloud_cleaner is None or not cloud_cleaner._available:
                logger.info(
                    "Mode Auto sans clé OpenAI : nettoyage regex/Ollama uniquement."
                )

        self.injector = TextInjector(mode=self.config["injection"])

        # Progressive injector : injection brut immédiat + remplacement par texte nettoyé
        from src.injection.progressive_injector import ProgressiveInjector
        self._prog_injector = ProgressiveInjector(self.injector)

        # Bridge thread-safe : le listener pynput tourne dans un thread arrière-plan.
        # Les signals Qt dispatchent _on_start/_on_stop vers le thread Qt principal.
        self._hotkey_bridge = _HotkeyBridge()
        self._hotkey_bridge.sig_start.connect(self._on_start)
        self._hotkey_bridge.sig_stop.connect(self._on_stop)
        self._hotkey_bridge.sig_busy.connect(self._on_hotkey_busy)

        # Bridge thread-safe pour les appels tray depuis les threads pipeline.
        self._pipeline_bridge = _PipelineBridge()
        self._pipeline_bridge.sig_tray_set_state.connect(self._on_tray_set_state)
        self._pipeline_bridge.sig_tray_notify.connect(self._on_tray_notify)
        self._pipeline_bridge.sig_update_available.connect(self._on_update_available)

        self.listener = HotkeyListener(
            hotkey=self.config["hotkey"],
            on_start=self._hotkey_bridge.sig_start.emit,
            on_stop=self._hotkey_bridge.sig_stop.emit,
            on_busy=self._hotkey_bridge.sig_busy.emit,
            debounce_delay=self.config.get("hotkey_debounce", 0.5),
        )

        # Licensing
        from src.licensing.validator import LicenseValidator
        licensing_config = self.config.get("licensing", {})
        self.license_validator = LicenseValidator(
            free_daily_limit=licensing_config.get("free_daily_limit", 50),
            free_limit=licensing_config.get("free_limit", 1000),
            cache_duration=licensing_config.get("cache_duration", 86400),
        )

        # Orb widget (QPainter natif — remplace QWebEngineView)
        from src.gui.orb_widget import OrbWidget
        self.waveform = OrbWidget(
            capture=self.capture,
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_settings=self._on_settings,
            on_quit=self._shutdown,
        )
        # Cacher l'icone Wave si le mode est "hotkey uniquement"
        if self.config.get("activation_method", "both") == "hotkey":
            self.waveform.hide()

        # System tray (PySide6 QSystemTrayIcon)
        from src.gui.tray_icon import TrayIcon
        self.tray = TrayIcon(
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_quit=self._shutdown,
            on_activate_license=self._activate_license_dialog,
            on_settings=self._on_settings,
            on_help=self._on_help,
            on_tray_clicked=self._on_settings,
            language=self.config.get("language", "en"),
        )
        self.tray.setup()

        # Health-check tray icon sur Linux (le panel peut crasher)
        if sys.platform != "win32":
            from PySide6.QtCore import QTimer
            self._tray_health_timer = QTimer()
            self._tray_health_timer.timeout.connect(self._check_tray_health)
            self._tray_health_timer.start(30_000)  # 30s

        # Health-check orb widget sur Windows (peut perdre always-on-top)
        if sys.platform == "win32" and self.waveform:
            from PySide6.QtCore import QTimer
            self._orb_health_timer = QTimer()
            self._orb_health_timer.timeout.connect(self._check_orb_health)
            self._orb_health_timer.start(30_000)  # 30s

        # Pre-warm en background : charger Whisper + verifier Ollama
        self._prewarm_engines()
        logger.info("VoxWave pret !")

    def _prewarm_engines(self) -> None:
        """Pre-charge les moteurs en background pour reduire la latence du premier appel."""
        def _prewarm_whisper() -> None:
            if hasattr(self.engine, 'preload'):
                try:
                    logger.info("Pre-warm: chargement modele Whisper...")
                    self.engine.preload()
                    logger.info("Pre-warm: modele Whisper charge")
                except Exception as e:
                    logger.warning(f"Pre-warm Whisper echec: {e}")

        def _prewarm_ollama() -> None:
            if self.pipeline and self.pipeline._local_cleaner:
                try:
                    available = self.pipeline._local_cleaner.is_available()
                    logger.info(f"Pre-warm: Ollama {'disponible' if available else 'indisponible'}")
                    if not available:
                        logger.warning("Pre-warm: Ollama indisponible, circuit breaker pre-ouvert")
                        self.pipeline._local_circuit.force_open()
                except Exception as e:
                    logger.warning(f"Pre-warm Ollama echec: {e}")

        def _check_cloud_connectivity() -> None:
            """Ping les APIs cloud et pre-ouvre les circuit breakers si injoignables."""
            import urllib.error
            import urllib.request
            # Check Groq
            if hasattr(self.engine, '_circuit'):
                try:
                    urllib.request.urlopen("https://api.groq.com", timeout=3)
                    logger.info("Pre-warm: Groq API joignable")
                except urllib.error.HTTPError:
                    # HTTP error = serveur joignable, juste pas de endpoint valide
                    logger.info("Pre-warm: Groq API joignable")
                except (urllib.error.URLError, OSError, TimeoutError):
                    logger.warning("Pre-warm: Groq API injoignable, circuit breaker pre-ouvert")
                    self.engine._circuit.force_open()
            # Check OpenAI
            if self.pipeline and self.pipeline._cloud_cleaner is not None:
                try:
                    urllib.request.urlopen("https://api.openai.com", timeout=3)
                    logger.info("Pre-warm: OpenAI API joignable")
                except urllib.error.HTTPError:
                    logger.info("Pre-warm: OpenAI API joignable")
                except (urllib.error.URLError, OSError, TimeoutError):
                    logger.warning("Pre-warm: OpenAI API injoignable, circuit breaker pre-ouvert")
                    self.pipeline._cloud_circuit.force_open()

        def _check_update() -> None:
            try:
                from src import __version__
                from src.utils.updater import check_for_update

                result = check_for_update(__version__)
                if result:
                    logger.info(f"Mise a jour disponible: v{result.version}")
                    self._pipeline_bridge.sig_update_available.emit(
                        result.version, result.download_url
                    )
            except Exception as e:
                logger.debug(f"Check update echec: {e}")

        self._executor.submit(_prewarm_whisper)
        self._executor.submit(_prewarm_ollama)
        self._executor.submit(_check_cloud_connectivity)
        self._executor.submit(_check_update)

    def _detect_ollama_host(self) -> str:
        """Scanne les ports courants d'Ollama et retourne le premier qui répond.

        Ports testés : 11434 (défaut), 11435, 11433.
        Timeout : 0.5s par port. Silencieux si aucun port ne répond.

        Returns:
            URL complète, ex: "http://localhost:11434"
        """
        import socket
        for port in [11434, 11435, 11433]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    sock.settimeout(0.5)
                    result = sock.connect_ex(("localhost", port))
                finally:
                    sock.close()
                if result == 0:
                    host = f"http://localhost:{port}"
                    if port != 11434:
                        logger.info(f"Ollama détecté sur port non-standard : {host}")
                    return host
            except Exception:
                pass
        return self.config.get("cleaning", {}).get("ollama_host", "http://localhost:11434")

    def _rebuild_pipeline(self) -> None:
        """Recrée le CleaningPipeline avec la config courante.

        Appelé quand le mode ou le provider change en cours de session,
        pour garantir que les cleaners LLM sont bien initialisés.
        """
        from src.cleaning.llm_cleaner import CleaningPipeline

        cleaning_config = self.config.get("cleaning", {})
        self.pipeline = CleaningPipeline(
            mode=cleaning_config["mode"],
            llm_model=cleaning_config["llm_model"],
            cloud_model=cleaning_config.get("cloud_model", "gpt-4o-mini"),
            cleaning_provider=cleaning_config.get("provider", "local"),
            language=self.config["whisper"]["language"],
            filler_words=cleaning_config.get("filler_words"),
            ollama_host=cleaning_config.get("ollama_host", "http://localhost:11434"),
            on_fallback=self._on_fallback,
        )
        logger.info(f"Pipeline recréé : mode={cleaning_config['mode']}, provider={cleaning_config.get('provider', 'local')}")

    def _create_transcription_engine(self, provider: str) -> object:
        """Cree le moteur de transcription selon le provider configure.

        Args:
            provider: hybrid, cloud, ou local.

        Returns:
            Instance du moteur de transcription.
        """
        language = self.config["whisper"]["language"]
        sample_rate = self.config["audio"]["sample_rate"]
        interface_lang = self.config.get("language", "en")

        if provider == "hybrid":
            from src.transcription.hybrid_engine import HybridTranscriptionEngine
            groq_model = self.config.get("groq", {}).get("model", "whisper-large-v3")
            return HybridTranscriptionEngine(
                groq_model=groq_model,
                local_model=self.config["whisper"]["model"],
                language=language,
                sample_rate=sample_rate,
                on_fallback=self._on_fallback,
                interface_language=interface_lang,
            )
        elif provider == "cloud":
            from src.transcription.groq_engine import GroqWhisperEngine
            groq_model = self.config.get("groq", {}).get("model", "whisper-large-v3")
            return GroqWhisperEngine(
                model=groq_model, language=language, sample_rate=sample_rate,
                interface_language=interface_lang,
            )
        else:
            from src.transcription.whisper_engine import WhisperEngine
            return WhisperEngine(
                model=self.config["whisper"]["model"],
                language=language,
                sample_rate=sample_rate,
                interface_language=interface_lang,
            )

    def _toggle_waveform(self) -> None:
        """Affiche ou cache le widget orb quand on clique sur l'icone tray."""
        if self.waveform:
            if self.waveform.isVisible():
                self.waveform.hide()
            else:
                self.waveform.show()
                self.waveform.raise_()

    def _on_start(self) -> None:
        """Callback: debut enregistrement."""
        # Capturer l'app active AVANT de démarrer l'enregistrement
        exe = get_active_exe()
        self._current_app_profile = get_app_profile(exe)
        logger.info(f"[context] App détectée: '{exe}' → profil '{self._current_app_profile}'")

        logger.info("Enregistrement...")
        self._stop_event.clear()
        self.feedback.play_start()
        if self.tray:
            self.tray.set_state("recording")
        if self.waveform:
            self.waveform.show_recording()
        self.capture.start()

    def _on_stop(self) -> None:
        """Callback: fin enregistrement -> lance le pipeline dans un thread."""
        logger.info("_on_stop appelé")
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        if self.tray:
            self.tray.set_state("processing")
        if self.waveform:
            self.waveform.show_processing()
            lang = self.config.get("language", "en")
            self.waveform.update_step(_app_t(lang, "processing"))
        self.capture.stop()
        audio = self.capture.get_buffer()
        self.capture.clear_buffer()

        if len(audio) == 0:
            logger.warning("Aucun audio capture")
            if self.waveform:
                self.waveform.show_idle()
                if self.config.get("activation_method", "both") == "hotkey":
                    self.waveform.sig_hide_widget.emit()
            return

        # Jouer le son stop en background (overlap avec debut du pipeline)
        self._executor.submit(self.feedback.play_stop)

        # Lancer le pipeline progressif dans un thread (injection brut < 800ms)
        self._processing_thread = threading.Thread(
            target=self._process_audio_progressive, args=(audio,), daemon=True,
        )
        self._processing_thread.start()

    def _on_hotkey_busy(self) -> None:
        """Feedback quand F8 est pressé pendant que le pipeline tourne."""
        lang = self.config.get("language", "en")
        msg = _BUSY_T.get(lang, _BUSY_T["en"])
        logger.info(f"Hotkey ignoré (pipeline en cours) — feedback tray: {msg}")
        if self.tray:
            self.tray.show_notification("VoxWave", msg)

    def _on_tray_set_state(self, state: str) -> None:
        """Slot thread principal : change l'état du tray (appelé via signal)."""
        if self.tray:
            self.tray.set_state(state)

    def _on_tray_notify(self, title: str, message: str) -> None:
        """Slot thread principal : affiche une notification tray (appelé via signal)."""
        if self.tray:
            self.tray.show_notification(title, message)

    def _on_update_available(self, version: str, download_url: str) -> None:
        """Slot thread principal : ajoute l'action update dans le tray + notification."""
        if self.tray:
            self.tray.add_update_action(version, download_url)
            lang = self.config.get("language", "en")
            msg = _UPDATE_NOTIF_T.get(lang, _UPDATE_NOTIF_T["en"]).format(
                version=version
            )
            self.tray.show_notification("VoxWave", msg)

    def _check_auto_stop(self) -> None:
        """Pollé par QTimer (100ms) sur le thread Qt principal.

        Vérifie si le thread audio a demandé un auto-stop via threading.Event.
        """
        if self._auto_stop_event.is_set():
            self._auto_stop_event.clear()
            logger.info("Auto-stop: event reçu sur thread Qt principal")
            self._on_stop()

    def _schedule_auto_stop(self) -> None:
        """Appelé depuis le thread audio (PortAudio C callback) — set un Event thread-safe.

        Les signaux Qt ne fonctionnent PAS depuis les threads C de PortAudio
        (contrairement aux threads Python comme pynput). On utilise un
        threading.Event pollé par un QTimer côté thread principal.
        """
        if self.capture.is_recording and not self._shutting_down:
            logger.info("Auto-stop: declenchement depuis thread audio")
            self._auto_stop_event.set()

    def _process_audio(self, audio) -> None:
        """Pipeline complet : transcription -> nettoyage -> injection (thread separe)."""
        if not self._processing_lock.acquire(blocking=False):
            logger.warning("Pipeline deja en cours, appui ignore")
            return
        self.listener.set_processing(True)
        had_error = False
        try:
            # Verifier la licence / free tier (le local n'est jamais bloque)
            transcription_provider = self.config.get("transcription", {}).get("provider", "local")
            if self.license_validator and not self.license_validator.increment_usage_for_provider(transcription_provider):
                msg = "Free tier epuise. Activez une licence pour continuer."
                logger.warning(msg)
                if self.tray:
                    self.tray.show_notification("VoxWave — Licence", msg)
                return

            audio_config = self.config["audio"]
            duration = len(audio) / audio_config["sample_rate"]
            min_duration = audio_config.get("min_audio_duration", 0.5)
            max_duration = audio_config.get("max_audio_duration", 300.0)
            logger.info(f"Audio capture: {duration:.2f}s")

            if duration < min_duration:
                logger.warning(f"Audio trop court ({duration:.2f}s < {min_duration}s), ignore")
                return

            if duration > max_duration:
                logger.warning(f"Audio trop long ({duration:.2f}s), tronque a {max_duration}s")
                max_samples = int(max_duration * audio_config["sample_rate"])
                audio = audio[:max_samples]

            # Preparer (apres troncature)
            audio = self.processor.prepare_for_whisper(audio)

            # Vérifier si de la parole a été détectée après le trim
            post_duration = len(audio) / audio_config["sample_rate"]
            if post_duration < min_duration:
                logger.info(f"Aucune parole detectee apres trim ({post_duration:.2f}s), ignore")
                return

            # Verifier la taille apres preparation (limite Groq API : 25MB WAV)
            audio_size_bytes = len(audio) * 2
            if audio_size_bytes > 24_000_000:
                max_safe_samples = 24_000_000 // 2
                logger.warning(f"Audio trop volumineux ({audio_size_bytes/1e6:.1f}MB), tronque pour API")
                audio = audio[:max_safe_samples]

            # Chunking si audio long
            chunking_threshold = self.config.get("audio", {}).get("chunking_threshold", 30.0)
            audio_duration = len(audio) / self.config["audio"]["sample_rate"]

            # Indicateur d'etape
            lang = self.config.get("language", "en")
            if self.waveform:
                self.waveform.update_step(_app_t(lang, "transcription"))

            if audio_duration > chunking_threshold:
                clean_text = self._process_chunked(audio)
            else:
                clean_text = self._transcribe_and_clean(audio)

            if not clean_text or not clean_text.strip():
                logger.warning("Texte final vide, ignore")
                return

            # Apercu transcription
            show_preview = self.config.get("gui", {}).get("show_transcription_preview", True)
            if self.waveform and show_preview:
                self.waveform.show_preview(clean_text)

            # Injecter
            if self.waveform:
                self.waveform.update_step(_app_t(lang, "injection"))
            self.injector.inject(clean_text)
            self.feedback.play_complete()
            logger.info("Texte injecte !")
        except Exception as e:
            had_error = True
            self.feedback.play_error()
            # Thread-safe : dispatcher vers le thread Qt principal via signal
            self._pipeline_bridge.sig_tray_set_state.emit("error")
            self._pipeline_bridge.sig_tray_notify.emit("VoxWave — Erreur", str(e))
            if self.waveform:
                _err_lang = self.config.get("language", "en")
                self.waveform.set_error_text(_ERROR_T.get(_err_lang, "Error"))
                self.waveform.show_error()  # revient a idle apres ERROR_DISPLAY_MS
                if self.config.get("activation_method", "both") == "hotkey":
                    self.waveform.sig_hide_widget.emit()
            from src.utils.exceptions import TranscriptionError, CleaningError
            if isinstance(e, TranscriptionError):
                logger.error(f"Erreur transcription: {e}")
            elif isinstance(e, CleaningError):
                logger.error(f"Erreur nettoyage: {e}")
            else:
                logger.error(f"Erreur pipeline inattendue: {e}", exc_info=True)
        finally:
            self._processing_lock.release()
            self.listener.set_processing(False)
            if not had_error:
                if self.waveform:
                    self.waveform.show_idle()
                    if self.config.get("activation_method", "both") == "hotkey":
                        # Signal thread-safe : le QTimer tourne dans le thread principal
                        self.waveform.sig_hide_widget_delayed.emit()
                # Thread-safe : dispatcher vers le thread Qt principal via signal
                self._pipeline_bridge.sig_tray_set_state.emit("idle")

    def _process_audio_progressive(self, audio) -> None:
        """Pipeline progressif : injection brut < 800ms, puis remplacement nettoyé ~1.1s.

        Flow :
            1. Validation (licence, durée audio)
            2. Groq transcription batch (~500ms)
            3. inject_raw() → texte visible immédiatement
            4. OpenAI streaming → replace_with_clean() en parallèle de la lecture
        """
        if not self._processing_lock.acquire(blocking=False):
            logger.warning("Pipeline déjà en cours, appui ignoré")
            return
        self.listener.set_processing(True)
        had_error = False
        t_start = time.time()

        try:
            # --- Vérification licence (le local n'est jamais bloqué) ---
            transcription_provider = self.config.get("transcription", {}).get("provider", "local")
            if self.license_validator and not self.license_validator.increment_usage_for_provider(transcription_provider):
                msg = "Free tier épuisé. Activez une licence pour continuer."
                logger.warning(msg)
                if self.tray:
                    self.tray.show_notification("VoxWave — Licence", msg)
                return

            # --- Validation durée audio ---
            audio_config = self.config["audio"]
            duration = len(audio) / audio_config["sample_rate"]
            min_duration = audio_config.get("min_audio_duration", 0.5)
            max_duration = audio_config.get("max_audio_duration", 300.0)
            logger.info(f"[progressif] Audio: {duration:.2f}s")

            if duration < min_duration:
                logger.warning(f"Audio trop court ({duration:.2f}s), ignoré")
                return

            if duration > max_duration:
                max_samples = int(max_duration * audio_config["sample_rate"])
                audio = audio[:max_samples]

            # --- Préparation audio ---
            audio = self.processor.prepare_for_whisper(audio)

            # Vérifier si de la parole a été détectée après le trim
            post_duration = len(audio) / audio_config["sample_rate"]
            if post_duration < min_duration:
                logger.info(f"[progressif] Aucune parole detectee apres trim ({post_duration:.2f}s), ignore")
                return

            # --- Étape 1 : Transcription batch Groq (~500ms) ---
            lang = self.config.get("language", "en")
            if self.waveform:
                self.waveform.update_step(_app_t(lang, "transcription"))

            t_groq = time.time()

            # Vérif taille WAV (limite Groq API : 25MB)
            if len(audio) * 2 > 24_000_000:
                audio = audio[:24_000_000 // 2]

            chunking_threshold = self.config.get("audio", {}).get("chunking_threshold", 30.0)
            audio_duration = len(audio) / audio_config["sample_rate"]

            if audio_duration > chunking_threshold:
                # Audio long : découper aux silences et transcrire chunk par chunk
                chunks = self.processor.split_at_silence(audio)
                raw_parts: list[str] = []
                for i, chunk in enumerate(chunks):
                    if self.waveform:
                        self.waveform.update_step(f"Transcription {i+1}/{len(chunks)}...")
                    part = self.engine.transcribe(chunk)
                    part = strip_hallucination_tails(part)
                    if part and part.strip() and not is_hallucination(part):
                        raw_parts.append(part.strip())
                    elif part and part.strip():
                        logger.info(f"[progressif] Chunk {i+1}/{len(chunks)} rejeté (hallucination): '{part.strip()}'")

                raw_text = " ".join(raw_parts)
            else:
                # Audio court : transcription directe
                raw_text = self.engine.transcribe(audio)
                raw_text = strip_hallucination_tails(raw_text)

            _trans_label = self.config.get("transcription", {}).get("provider", "local")
            logger.info(f"[progressif] Transcription ({_trans_label}): {(time.time()-t_groq)*1000:.0f}ms → '{raw_text}'")

            if not raw_text or not raw_text.strip():
                logger.warning("[progressif] Transcription vide, ignoré")
                return

            if is_hallucination(raw_text):
                logger.warning(f"[progressif] Hallucination ignorée: {raw_text}")
                return

            # Adapter les filler words à la langue détectée
            detected_lang = getattr(self.engine, "last_detected_language", None)
            if detected_lang:
                self.pipeline.regex_cleaner.set_language(detected_lang)
                self.pipeline.language = detected_lang

            # --- Étape 2 : Injection immédiate du texte brut ---
            if self.waveform:
                self.waveform.update_step(_app_t(lang, "injection"))

            t_inject = time.time()
            self._prog_injector.inject_raw(raw_text)
            logger.info(
                f"[progressif] Texte brut injecté: {(time.time()-t_inject)*1000:.0f}ms "
                f"(total depuis fin parole: {(time.time()-t_start)*1000:.0f}ms)"
            )

            # Mettre l'icône en mode "traitement" pendant le nettoyage
            if self.tray:
                self.tray.set_state("processing")

            # --- Étape 3 : Nettoyage streaming + remplacement ---
            cloud_cleaner = getattr(self.pipeline, "_cloud_cleaner", None)
            if cloud_cleaner is not None and not cloud_cleaner._available:
                logger.warning("[progressif] _cloud_cleaner indisponible — OPENAI_API_KEY manquante dans .env")

            cleaning_mode = self.config.get("cleaning", {}).get("mode", "auto")
            app_profile = getattr(self, "_current_app_profile", "default")

            if cleaning_mode == "raw":
                # Mode brut : pas de remplacement — stopper le watcher pour éviter le leak
                self._prog_injector._stop_user_watch()

            else:  # Mode auto (+ compat verbatim/quality si config non migrée)
                # Profil "code" : skip LLM, regex seulement
                if app_profile == "code":
                    logger.info("[progressif] Profil 'code' → verbatim uniquement")
                    # Profil code : regex uniquement, jamais Ollama (trop lent)
                    _regex_result = self.pipeline.regex_cleaner.clean(raw_text)
                    clean_text = self.pipeline._clean_verbatim(_regex_result)
                    if clean_text and clean_text.strip() and clean_text != raw_text:
                        self._prog_injector.replace_with_clean(raw_text, iter([clean_text]))
                    else:
                        self._prog_injector._stop_user_watch()

                elif (cloud_cleaner is not None
                      and cloud_cleaner._available
                      and self.pipeline._cloud_circuit.should_allow_request()):
                    # Chemin rapide : OpenAI streaming contextuel (~300ms) + remplacement
                    if self.waveform:
                        self.waveform.update_step(_app_t(lang, "cleaning"))
                    t_clean = time.time()
                    clean_gen = cloud_cleaner.clean_streaming(raw_text, context_profile=app_profile)
                    self._prog_injector.replace_with_clean(raw_text, clean_gen)
                    logger.info(
                        f"[progressif] Remplacement nettoyé [{app_profile}]: "
                        f"{(time.time()-t_clean)*1000:.0f}ms "
                        f"(total: {(time.time()-t_start)*1000:.0f}ms)"
                    )
                else:
                    # Fallback : nettoyage synchrone via pipeline (regex / Ollama)
                    clean_text = self.pipeline.clean(raw_text, context_profile=app_profile)
                    if clean_text and clean_text.strip() and clean_text != raw_text:
                        self._prog_injector.replace_with_clean(raw_text, iter([clean_text]))
                    else:
                        self._prog_injector._stop_user_watch()

            self.feedback.play_complete()
            logger.info(f"[progressif] Pipeline terminé en {(time.time()-t_start)*1000:.0f}ms")

        except Exception as e:
            had_error = True
            self.feedback.play_error()
            # Thread-safe : dispatcher vers le thread Qt principal via signal
            self._pipeline_bridge.sig_tray_set_state.emit("error")
            self._pipeline_bridge.sig_tray_notify.emit("VoxWave — Erreur", str(e))
            if self.waveform:
                _err_lang = self.config.get("language", "en")
                self.waveform.set_error_text(_ERROR_T.get(_err_lang, "Error"))
                self.waveform.show_error()
                if self.config.get("activation_method", "both") == "hotkey":
                    self.waveform.sig_hide_widget.emit()
            from src.utils.exceptions import TranscriptionError, CleaningError
            if isinstance(e, TranscriptionError):
                logger.error(f"[progressif] Erreur transcription: {e}")
            elif isinstance(e, CleaningError):
                logger.error(f"[progressif] Erreur nettoyage: {e}")
            else:
                logger.error(f"[progressif] Erreur inattendue: {e}", exc_info=True)
        finally:
            self._processing_lock.release()
            self.listener.set_processing(False)
            if not had_error:
                if self.waveform:
                    self.waveform.show_idle()
                    if self.config.get("activation_method", "both") == "hotkey":
                        # Signal thread-safe : le QTimer tourne dans le thread principal
                        self.waveform.sig_hide_widget_delayed.emit()
                # Thread-safe : dispatcher vers le thread Qt principal via signal
                self._pipeline_bridge.sig_tray_set_state.emit("idle")

    def _transcribe_and_clean(self, audio) -> Optional[str]:
        """Transcrit et nettoie un segment audio.

        Args:
            audio: Buffer audio float32.

        Returns:
            Texte nettoye ou None.
        """
        # Transcrire
        raw_text = self.engine.transcribe(audio)
        raw_text = strip_hallucination_tails(raw_text)
        logger.info(f"Brut: {raw_text}")

        # Adapter les filler words a la langue detectee
        detected_lang = getattr(self.engine, "last_detected_language", None)
        if detected_lang:
            self.pipeline.regex_cleaner.set_language(detected_lang)
            self.pipeline.language = detected_lang

        if not raw_text.strip():
            logger.warning("Transcription vide")
            return None

        # Filtrer les hallucinations connues de Whisper
        if is_hallucination(raw_text):
            logger.warning(f"Hallucination detectee, ignore: {raw_text}")
            return None

        # Nettoyer
        if self.waveform:
            self.waveform.update_step(_app_t(self.config.get("language", "en"), "cleaning"))
        clean_text = self.pipeline.clean(raw_text)
        logger.info(f"Propre: {clean_text}")

        if not clean_text.strip():
            logger.warning("Texte nettoye vide, ignore")
            return None

        return clean_text

    def _process_chunked(self, audio) -> Optional[str]:
        """Traite un audio long par chunks avec progress.

        Args:
            audio: Buffer audio float32.

        Returns:
            Texte complet nettoye ou None.
        """
        chunks = self.processor.split_at_silence(audio)
        total = len(chunks)
        logger.info(f"Traitement chunke: {total} chunks")

        results = []
        for i, chunk in enumerate(chunks):
            if self.waveform:
                self.waveform.update_step(f"Transcription {i+1}/{total}...")
            result = self._transcribe_and_clean(chunk)
            if result:
                results.append(result)

        if not results:
            return None

        return " ".join(results)

    def _activate_license_dialog(self) -> None:
        """Ouvre un dialog pour saisir la cle de licence."""
        try:
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(
                None, "VoxWave — Activer licence",
                "Entrez votre cle de licence :"
            )
            if ok and text.strip():
                try:
                    self.license_validator.activate_license(text.strip())
                    if self.tray:
                        self.tray.show_notification("VoxWave", "Licence activee avec succes !")
                except Exception as e:
                    logger.error(f"Activation echouee: {e}")
                    if self.tray:
                        self.tray.show_notification("VoxWave — Erreur", f"Activation echouee : {e}")
        except Exception as e:
            logger.error(f"Dialog licence echoue: {e}")

    def _focus_existing_dialog(self, dialog: object, origin: str = "settings") -> None:
        """Ramene un dialog existant au premier plan avec retries sous Windows."""
        if dialog is None:
            return

        def _attempt(label: str) -> None:
            try:
                if hasattr(dialog, "isMinimized") and dialog.isMinimized():
                    dialog.showNormal()
                dialog.show()
                dialog.raise_()
                dialog.activateWindow()
                _force_foreground_win32(dialog)
                logger.debug(f"{origin}: focus attempt '{label}'")
            except RuntimeError as e:
                logger.debug(f"{origin}: focus ignore ({label}) - dialog ferme: {e}")
            except Exception as e:
                logger.debug(f"{origin}: focus echec ({label}): {e}")

        _attempt("immediate")

        if sys.platform == "win32":
            from PySide6.QtCore import QTimer
            QTimer.singleShot(50, lambda: _attempt("retry-50ms"))
            QTimer.singleShot(150, lambda: _attempt("retry-150ms"))

    def _on_settings(self) -> None:
        """Ouvre le dialogue des parametres et applique les changements."""
        if self._shutting_down:
            return

        # Guard singleton : si un dialog est deja ouvert, le mettre au premier plan
        if self._settings_dialog is not None:
            self._focus_existing_dialog(self._settings_dialog, origin="settings-existing")
            return

        from src.gui.settings_dialog import SettingsDialog

        cleaning_config = self.config.get("cleaning", {})
        dialog = SettingsDialog(
            current_hotkey=self.config["hotkey"],
            current_cleaning_mode=cleaning_config.get("mode", "verbatim"),
            current_language=self.config.get("whisper", {}).get("language", "en"),
            current_system_language=self.config.get("language", "en"),
            current_device_id=self.config.get("audio", {}).get("device_id"),
            current_transcription_provider=self.config.get("transcription", {}).get("provider", "hybrid"),
            current_cleaning_provider=cleaning_config.get("provider", "hybrid"),
            current_ollama_host=cleaning_config.get("ollama_host", "http://localhost:11434"),
            current_activation_method=self.config.get("activation_method", "both"),
            current_auto_stop_enabled=self.config.get("audio", {}).get("auto_stop_enabled", False),
            current_auto_stop_silence_duration=self.config.get("audio", {}).get("auto_stop_silence_duration", 2.0),
            on_quit=self._shutdown,
            on_activate_license=self._activate_license_dialog,
            parent=None,
        )
        self._settings_dialog = dialog
        self._focus_existing_dialog(dialog, origin="settings-new")
        dialog.exec()  # on lance toujours (fermeture avec X ou Save sauvegarde quand meme)
        self._settings_dialog = None
        self._apply_dialog_changes(dialog, cleaning_config)

    def _on_help(self) -> None:
        """Ouvre les parametres sur l'onglet Aide."""
        if self._shutting_down:
            return

        # Guard singleton : si un dialog est deja ouvert, le mettre au premier plan
        if self._settings_dialog is not None:
            self._focus_existing_dialog(self._settings_dialog, origin="help-existing")
            return

        from src.gui.settings_dialog import SettingsDialog

        cleaning_config = self.config.get("cleaning", {})
        dialog = SettingsDialog(
            current_hotkey=self.config["hotkey"],
            current_cleaning_mode=cleaning_config.get("mode", "verbatim"),
            current_language=self.config.get("whisper", {}).get("language", "en"),
            current_system_language=self.config.get("language", "en"),
            current_device_id=self.config.get("audio", {}).get("device_id"),
            current_transcription_provider=self.config.get("transcription", {}).get("provider", "hybrid"),
            current_cleaning_provider=cleaning_config.get("provider", "hybrid"),
            current_ollama_host=cleaning_config.get("ollama_host", "http://localhost:11434"),
            current_activation_method=self.config.get("activation_method", "both"),
            current_auto_stop_enabled=self.config.get("audio", {}).get("auto_stop_enabled", False),
            current_auto_stop_silence_duration=self.config.get("audio", {}).get("auto_stop_silence_duration", 2.0),
            on_quit=self._shutdown,
            on_activate_license=self._activate_license_dialog,
            parent=None,
        )
        self._settings_dialog = dialog
        dialog.navigate_to_help()
        self._focus_existing_dialog(dialog, origin="help-new")
        dialog.exec()
        self._settings_dialog = None
        # Appliquer les changements éventuels (l'utilisateur peut naviguer
        # vers d'autres onglets depuis l'onglet Aide)
        self._apply_dialog_changes(dialog, cleaning_config)

    def _apply_dialog_changes(self, dialog, cleaning_config: dict) -> None:
        """Applique les changements du SettingsDialog à la config et aux composants.

        Appelé par _on_settings et _on_help après dialog.exec().

        Args:
            dialog: Instance de SettingsDialog fermé.
            cleaning_config: Snapshot de self.config["cleaning"] pris avant exec().
        """
        changes = []

        # Hotkey
        new_hotkey = dialog.hotkey
        if new_hotkey != self.config["hotkey"]:
            self.config["hotkey"] = new_hotkey
            if self.listener:
                self.listener.update_hotkey(new_hotkey)
            self._save_config("hotkey", new_hotkey)
            changes.append(f"Raccourci : {new_hotkey}")

        # Cleaning mode
        new_mode = dialog.cleaning_mode
        if new_mode != cleaning_config.get("mode"):
            self.config.setdefault("cleaning", {})["mode"] = new_mode
            self._save_config_nested("cleaning", "mode", new_mode)
            self._rebuild_pipeline()
            mode_names = {"raw": "Brut", "auto": "Auto"}
            changes.append(f"Mode : {mode_names.get(new_mode, new_mode)}")

        # System language (interface)
        new_sys_lang = dialog.system_language
        if new_sys_lang != self.config.get("language"):
            self.config["language"] = new_sys_lang
            self._save_config("language", new_sys_lang)
            if self.tray:
                self.tray.update_language(new_sys_lang)
            # Mettre a jour le hint langue dans le moteur de transcription
            if hasattr(self.engine, "_interface_language"):
                self.engine._interface_language = new_sys_lang
            if hasattr(self.engine, "_groq_engine") and self.engine._groq_engine:
                self.engine._groq_engine._interface_language = new_sys_lang
            changes.append(f"Interface : {new_sys_lang}")

        # Dictation language
        new_lang = dialog.language
        if new_lang != self.config.get("whisper", {}).get("language"):
            self.config.setdefault("whisper", {})["language"] = new_lang
            self._save_config_nested("whisper", "language", new_lang)
            # Mettre a jour le moteur a runtime (sans redemarrer)
            if hasattr(self.engine, "language"):
                self.engine.language = new_lang
            if self.pipeline and hasattr(self.pipeline, "language"):
                self.pipeline.language = new_lang
                self.pipeline.regex_cleaner.set_language(new_lang)
            changes.append(f"Dictee : {new_lang}")

        # Device ID
        new_device = dialog.device_id
        if new_device != self.config.get("audio", {}).get("device_id"):
            self.config.setdefault("audio", {})["device_id"] = new_device
            self._save_config_nested("audio", "device_id", new_device)
            changes.append("Micro change")

        # Transcription provider
        new_trans = dialog.transcription_provider
        if new_trans != self.config.get("transcription", {}).get("provider"):
            self.config.setdefault("transcription", {})["provider"] = new_trans
            self._save_config_nested("transcription", "provider", new_trans)
            self.engine = self._create_transcription_engine(new_trans)
            changes.append(f"Transcription : {new_trans}")

        # Cleaning provider
        new_clean = dialog.cleaning_provider
        if new_clean != cleaning_config.get("provider"):
            self.config.setdefault("cleaning", {})["provider"] = new_clean
            self._save_config_nested("cleaning", "provider", new_clean)
            self._rebuild_pipeline()
            changes.append(f"Nettoyage : {new_clean}")

        # Ollama host
        new_ollama_host = dialog.ollama_host
        if new_ollama_host != cleaning_config.get("ollama_host"):
            self.config.setdefault("cleaning", {})["ollama_host"] = new_ollama_host
            self._save_config_nested("cleaning", "ollama_host", new_ollama_host)
            self._rebuild_pipeline()
            changes.append(f"Ollama : {new_ollama_host}")

        # Activation method (hotkey / icon / both)
        new_activation = dialog.activation_method
        if new_activation != self.config.get("activation_method", "both"):
            self.config["activation_method"] = new_activation
            self._save_config("activation_method", new_activation)
            if new_activation == "hotkey":
                if self.waveform:
                    self.waveform.hide()
                if self.listener:
                    self.listener.start()
            elif new_activation == "icon":
                if self.waveform:
                    self.waveform.show()
                if self.listener:
                    self.listener.stop()
            else:  # "both"
                if self.waveform:
                    self.waveform.show()
                if self.listener:
                    self.listener.start()
            changes.append(f"Activation : {new_activation}")

        # Auto-stop
        new_auto_stop = dialog.auto_stop_enabled
        new_auto_stop_dur = dialog.auto_stop_silence_duration
        audio_config = self.config.setdefault("audio", {})
        if new_auto_stop != audio_config.get("auto_stop_enabled", False):
            audio_config["auto_stop_enabled"] = new_auto_stop
            self._save_config_nested("audio", "auto_stop_enabled", new_auto_stop)
            self.capture.update_auto_stop(new_auto_stop, new_auto_stop_dur)
            state = "active" if new_auto_stop else "desactive"
            changes.append(f"Auto-stop : {state}")
        if new_auto_stop_dur != audio_config.get("auto_stop_silence_duration", 2.0):
            audio_config["auto_stop_silence_duration"] = new_auto_stop_dur
            self._save_config_nested("audio", "auto_stop_silence_duration", new_auto_stop_dur)
            self.capture.update_auto_stop(new_auto_stop, new_auto_stop_dur)
            changes.append(f"Silence : {new_auto_stop_dur}s")

        if changes and self.tray:
            self.tray.show_notification("VoxWave", "Parametres mis a jour")
        logger.info(f"Settings: {', '.join(changes) if changes else 'aucun changement'}")

    def _save_config(self, key: str, value: object) -> None:
        """Sauvegarde un champ dans config.yaml en preservant le reste.

        Args:
            key: Cle de premier niveau a mettre a jour.
            value: Nouvelle valeur.
        """
        from src.utils.platform import user_config_path

        config_path = user_config_path()
        try:
            with open(config_path, "r") as f:
                lines = f.readlines()

            # Chercher et remplacer la ligne correspondante
            new_lines = []
            found = False
            for line in lines:
                if line.startswith(f"{key}:"):
                    new_lines.append(f"{key}: {value}\n")
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                new_lines.append(f"{key}: {value}\n")

            with open(config_path, "w") as f:
                f.writelines(new_lines)

            logger.info(f"Config sauvegardee: {key}={value}")
        except Exception as e:
            logger.error(f"Erreur sauvegarde config: {e}")

    def _save_config_nested(self, section: str, key: str, value: object) -> None:
        """Sauvegarde une cle nested dans config.yaml (ex: cleaning.mode).

        Charge le YAML complet, modifie la cle, et re-ecrit le fichier.

        Args:
            section: Section de premier niveau (ex: "cleaning").
            key: Cle dans la section (ex: "mode").
            value: Nouvelle valeur.
        """
        from src.utils.platform import user_config_path

        config_path = user_config_path()
        try:
            with open(config_path, "r") as f:
                data = yaml.safe_load(f) or {}

            if section not in data:
                data[section] = {}
            data[section][key] = value

            with open(config_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            logger.info(f"Config sauvegardee: {section}.{key}={value}")
        except Exception as e:
            logger.error(f"Erreur sauvegarde config nested: {e}")

    def _on_fallback(self, message: str) -> None:
        """Affiche une notification de fallback via le tray.

        Args:
            message: Message de fallback a afficher.
        """
        logger.info(f"Fallback: {message}")
        if self.tray:
            self.tray.show_notification("VoxWave", message)

    def _on_taskbar_created(self) -> None:
        """Appele quand Explorer redemarre — recree le tray icon."""
        if self.tray:
            self.tray.reshow()
        # Re-forcer l'icone taskbar aussi
        if hasattr(self, '_taskbar') and sys.platform == "win32":
            from PySide6.QtCore import QTimer
            from src.gui.icons import force_taskbar_icon_win32
            hwnd = int(self._taskbar._win.winId())
            QTimer.singleShot(300, lambda: force_taskbar_icon_win32(hwnd))

    def _check_tray_health(self) -> None:
        """Verifie que le tray icon est visible (Linux)."""
        if self.tray and self.tray._tray and not self.tray._tray.isVisible():
            logger.warning("Tray icon invisible — tentative reshow")
            self.tray.reshow()

    def _check_orb_health(self) -> None:
        """Verifie que l'orb widget est visible et topmost en mode both/orb."""
        activation = self.config.get("activation_method", "both")
        if activation == "hotkey" or not self.waveform:
            return
        if not self.waveform.isVisible():
            logger.warning("Orb invisible en mode %s — re-show", activation)
            self.waveform.show()
        self.waveform.raise_()
        self.waveform.ensure_topmost()

    def _shutdown(self) -> None:
        """Arrete proprement tous les composants (idempotent)."""
        if self._shutting_down:
            return
        self._shutting_down = True
        logger.info("Arret VoxWave...")
        if self.listener:
            self.listener.stop()
        if self._processing_thread and self._processing_thread.is_alive():
            logger.info("Attente fin du pipeline en cours...")
            self._processing_thread.join(timeout=10)
            if self._processing_thread.is_alive():
                logger.warning("Pipeline toujours en cours apres 10s, arret force")
        if self.capture:
            self.capture.stop()
        if self.waveform:
            self.waveform.show_idle()
        # Shutdown executor
        self._executor.shutdown(wait=False)
        # Stopper les health-checks
        if hasattr(self, '_tray_health_timer'):
            self._tray_health_timer.stop()
        if hasattr(self, '_orb_health_timer'):
            self._orb_health_timer.stop()
        # Stopper le tray icon proprement
        if self.tray:
            self.tray.stop()
        # Cacher la fenetre taskbar pour stopper les SC_RESTORE apres shutdown
        if hasattr(self, '_taskbar'):
            self._taskbar._win.hide()
        # Quitter la boucle Qt
        if self._qt_app:
            self._qt_app.quit()

    def run(self) -> None:
        """Lance l'application avec boucle Qt."""
        # VoxWave cible Windows et Linux uniquement
        if sys.platform == "darwin":
            logger.error("VoxWave n'est pas supporte sur macOS. Utilisez Windows ou Linux.")
            print("VoxWave n'est pas supporte sur macOS.")
            print("Plateformes supportees : Windows, Linux.")
            sys.exit(1)

        # Lock file anti-double-instance
        self._lock_file = None
        lock_path = os.path.join(
            os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
            "voxwave", ".lock",
        )
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        self._lock_file = open(lock_path, "w")
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            logger.warning("VoxWave est deja en cours d'execution, fermeture")
            sys.exit(0)

        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        self._qt_app = QApplication.instance() or QApplication(sys.argv)
        self._qt_app.setQuitOnLastWindowClosed(False)
        from src.gui.icons import create_qicon
        _app_icon = create_qicon("idle")
        self._qt_app.setWindowIcon(_app_icon)
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.voxwave.app")
        self._taskbar = _TaskbarWindow(
            on_activate=self._on_settings,
            app_icon=_app_icon,
            on_taskbar_created=self._on_taskbar_created,
        )
        self.initialize()

        # Welcome screen au premier lancement
        if self.config.get("first_launch", True):
            from src.gui.welcome_dialog import WelcomeDialog
            dialog = WelcomeDialog(
                current_hotkey=self.config["hotkey"],
                engine=self.engine,
                processor=self.processor,
                feedback=self.feedback,
                parent=None,
            )
            if dialog.exec():
                # Appliquer le hotkey choisi
                new_hotkey = dialog.hotkey
                if new_hotkey != self.config["hotkey"]:
                    self.config["hotkey"] = new_hotkey
                    if self.listener:
                        self.listener.update_hotkey(new_hotkey)
                    self._save_config("hotkey", new_hotkey)
                # Appliquer le mode de nettoyage choisi
                new_mode = dialog.cleaning_mode
                if new_mode != self.config.get("cleaning", {}).get("mode"):
                    self.config.setdefault("cleaning", {})["mode"] = new_mode
                    self._save_config_nested("cleaning", "mode", new_mode)
                    self._rebuild_pipeline()
                # Appliquer la langue d'interface
                new_lang = dialog.language
                if new_lang != self.config.get("language"):
                    self.config["language"] = new_lang
                    self._save_config("language", new_lang)
                # Appliquer la langue de dictee (separee)
                new_dict_lang = dialog.dictation_language
                if new_dict_lang != self.config.get("whisper", {}).get("language"):
                    self.config.setdefault("whisper", {})["language"] = new_dict_lang
                    self._save_config_nested("whisper", "language", new_dict_lang)
                # Marquer le premier lancement comme termine
                self.config["first_launch"] = False
                self._save_config("first_launch", "false")

        if self.config.get("activation_method", "both") != "icon":
            self.listener.start()

        # Signal handlers pour shutdown propre (Ctrl+C, SIGTERM)
        def _signal_handler(signum: int, frame: object) -> None:
            sig_name = signal.Signals(signum).name
            logger.info(f"Signal {sig_name} recu, arret en cours...")
            self._shutdown()

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        # QTimer no-op pour que Python puisse traiter les signaux
        # pendant la boucle Qt (sinon exec() bloque les handlers)
        self._signal_timer = QTimer()
        self._signal_timer.timeout.connect(lambda: None)
        self._signal_timer.start(500)

        # QTimer polling pour l'auto-stop (thread PortAudio → thread Qt)
        # Les signaux Qt ne traversent pas les threads C de PortAudio,
        # donc on poll un threading.Event toutes les 100ms.
        self._auto_stop_timer = QTimer()
        self._auto_stop_timer.timeout.connect(self._check_auto_stop)
        self._auto_stop_timer.start(100)
        logger.info("Auto-stop QTimer polling démarré (100ms)")

        logger.info(f"VoxWave actif ! Hotkey: {self.config['hotkey']} — Fermez le tray pour quitter.")
        self._qt_app.exec()


def test_microphone(config: dict) -> None:
    """Test rapide du microphone."""
    from src.audio.capture import AudioCapture
    import numpy as np

    print("Test du microphone (3 secondes)...")
    capture = AudioCapture(
        sample_rate=config["audio"]["sample_rate"],
        channels=config["audio"]["channels"],
    )
    capture.start()
    time.sleep(3)
    capture.stop()
    audio = capture.get_buffer()

    if len(audio) == 0:
        print("Aucun audio capture ! Verifiez votre micro.")
    else:
        volume = np.abs(audio).mean()
        duration = len(audio) / config["audio"]["sample_rate"]
        print(f"Audio capture: {duration:.1f}s, volume moyen: {volume:.4f}")
        if volume < 0.001:
            print("Volume tres faible. Verifiez votre micro.")
        else:
            print("Micro OK !")


@click.command()
@click.option("--model", default=None, help="Modele Whisper (tiny/base/small/medium/large-v3)")
@click.option("--test", is_flag=True, help="Test du microphone")
@click.option("--list-devices", is_flag=True, help="Liste les peripheriques audio")
@click.option("--config", "config_path", default="config.yaml", help="Chemin config")
@click.option("--log-level", default=None, help="Niveau de log")
def main(model, test, list_devices, config_path, log_level):
    """VoxWave — Dictee vocale intelligente."""
    effective_log_level = log_level or os.getenv("VOXWAVE_LOG_LEVEL", "INFO")
    setup_logging(effective_log_level)
    config = load_config(config_path)

    if list_devices:
        from src.audio.device_manager import AudioDeviceManager
        AudioDeviceManager.print_devices()
        return

    if model:
        config["whisper"]["model"] = model

    if test:
        test_microphone(config)
        return

    app = VoxWave(config)
    app.run()


if __name__ == "__main__":
    main()
