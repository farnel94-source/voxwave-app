"""Widget Voice Input pour feedback visuel pendant la dictee.

Affiche une fenetre frameless, always-on-top, deplacable, avec une icone micro
qui se transforme en barre de frequences animees pendant l'enregistrement.
3 etats : idle (icone micro), recording (barres animees + timer), processing (traitement).
"""

import logging
import os
import sys
from typing import Callable, Optional

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from src.utils.platform import resource_path

logger = logging.getLogger(__name__)

WIDGET_WIDTH = 300
WIDGET_HEIGHT = 116
ERROR_DISPLAY_MS = 3000


def _restore_foreground_window() -> Optional[Callable]:
    """Capture la fenetre active et retourne une fonction pour la restaurer.

    Returns:
        Callable qui restaure le focus, ou None si non-Windows.
    """
    if sys.platform == "darwin":
        logger.warning("restore_foreground: macOS non supporte par The Wave")
        return None
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd:
            def restore():
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            return restore
    except Exception:
        pass
    return None


class Bridge(QObject):
    """Pont Python <-> JS via QWebChannel."""

    amplitude_changed = Signal(float)
    state_changed = Signal(str)

    def __init__(
        self,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        on_settings: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
        widget: Optional["WaveformWidget"] = None,
    ) -> None:
        """Initialise le bridge.

        Args:
            on_start: Callback appelee quand l'icone micro est cliquee.
            on_stop: Callback appelee quand le stop est clique.
            on_settings: Callback appelee quand les parametres sont demandes.
            on_quit: Callback appelee quand le quit est demande.
        """
        super().__init__()
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._widget = widget
        self._saved_restore: Optional[Callable] = None

    @Slot()
    def on_start_clicked(self) -> None:
        """Appelee depuis JS quand le logo est clique (idle -> recording).

        Sauvegarde la fenetre active pour pouvoir restaurer le focus
        au moment du stop (injection de texte).
        """
        logger.debug("Bridge: start clicked")
        self._saved_restore = _restore_foreground_window()
        if self._on_start:
            self._on_start()
        # Restaurer le focus immediatement apres le start
        if self._saved_restore:
            QTimer.singleShot(100, self._saved_restore)

    @Slot()
    def on_stop_clicked(self) -> None:
        """Appelee depuis JS quand le logo est clique (recording -> stop).

        Restaure la fenetre active sauvegardee au start pour que l'injection
        de texte se fasse dans la bonne fenetre.
        """
        logger.debug("Bridge: stop clicked")
        if self._on_stop:
            self._on_stop()
        # Restaurer la fenetre de l'utilisateur (sauvegardee au start)
        if self._saved_restore:
            QTimer.singleShot(100, self._saved_restore)
            self._saved_restore = None

    @Slot()
    def on_settings_clicked(self) -> None:
        """Appelee depuis JS quand clic droit sur le logo."""
        logger.debug("Bridge: settings clicked")
        if self._on_settings:
            self._on_settings()

    @Slot()
    def on_quit_clicked(self) -> None:
        """Appelee depuis JS pour quitter (reserve pour usage futur)."""
        logger.debug("Bridge: quit clicked")
        if self._on_quit:
            self._on_quit()

    @Slot(int, int)
    def move_by(self, dx: int, dy: int) -> None:
        """Deplace le widget parent de (dx, dy) pixels.

        Appelee depuis JS pendant le drag de l'icone.
        """
        if self._widget:
            pos = self._widget.pos()
            self._widget.move(pos.x() + dx, pos.y() + dy)


class WaveformWidget(QWidget):
    """Widget flottant Voice Input deplacable."""

    # Signals pour communication thread-safe
    sig_show_recording = Signal()
    sig_show_processing = Signal()
    sig_show_idle = Signal()
    sig_show_error = Signal()
    sig_update_step = Signal(str)
    sig_show_preview = Signal(str)

    def __init__(
        self,
        capture: Optional[object] = None,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        on_settings: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
    ) -> None:
        """Initialise le widget Voice Input.

        Args:
            capture: Instance AudioCapture pour lire l'amplitude en temps reel.
            on_start: Callback quand l'icone micro est cliquee.
            on_stop: Callback quand le stop est clique.
            on_settings: Callback quand les parametres sont demandes (clic droit logo).
            on_quit: Callback quand le quit est demande (via tray icon).
        """
        super().__init__()
        self._capture = capture
        self._state: str = "idle"
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._setup_window()
        self._setup_webview()
        self._setup_timers()
        self._connect_signals()
        self.show()

    def _setup_window(self) -> None:
        """Configure la fenetre frameless, always-on-top, transparente."""
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(WIDGET_WIDTH, WIDGET_HEIGHT)
        self._center_bottom()

    def _center_bottom(self) -> None:
        """Positionne le widget en bas-centre de l'ecran."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - WIDGET_WIDTH) // 2
            y = geo.y() + geo.height() - WIDGET_HEIGHT - 40
            self.move(x, y)

    def _setup_webview(self) -> None:
        """Configure QWebEngineView avec le bridge QWebChannel."""
        self._bridge = Bridge(
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_settings=self._on_settings,
            on_quit=self._on_quit,
            widget=self,
        )

        self._web_view = QWebEngineView(self)
        self._web_view.setStyleSheet("background: transparent;")
        self._web_view.page().setBackgroundColor(Qt.transparent)

        # QWebChannel
        self._channel = QWebChannel()
        self._channel.registerObject("bridge", self._bridge)
        self._web_view.page().setWebChannel(self._channel)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web_view)

        # Charger orb.html
        orb_path = resource_path(os.path.join("src", "gui", "orb", "orb.html"))
        self._web_view.setUrl(QUrl.fromLocalFile(orb_path))
        logger.debug(f"Voice Input HTML charge: {orb_path}")

    def _setup_timers(self) -> None:
        """Configure le timer pour envoyer l'amplitude au JS."""
        self._amplitude_timer = QTimer(self)
        self._amplitude_timer.setInterval(50)
        self._amplitude_timer.timeout.connect(self._send_amplitude)

    def _connect_signals(self) -> None:
        """Connecte les signals pour les appels thread-safe."""
        self.sig_show_recording.connect(self._do_show_recording)
        self.sig_show_processing.connect(self._do_show_processing)
        self.sig_show_idle.connect(self._do_show_idle)
        self.sig_show_error.connect(self._do_show_error)
        self.sig_update_step.connect(self._do_update_step)
        self.sig_show_preview.connect(self._do_show_preview)

    # === Public API (thread-safe) ===

    def show_recording(self) -> None:
        """Affiche le widget en mode recording (thread-safe)."""
        self.sig_show_recording.emit()

    def show_processing(self) -> None:
        """Affiche le widget en mode processing (thread-safe)."""
        self.sig_show_processing.emit()

    def show_idle(self) -> None:
        """Retourne a l'etat idle (thread-safe)."""
        self.sig_show_idle.emit()

    def show_error(self) -> None:
        """Affiche l'etat erreur pendant 3s puis revient a idle (thread-safe)."""
        self.sig_show_error.emit()

    def update_step(self, step_text: str) -> None:
        """Met a jour l'indicateur d'etape (thread-safe).

        Args:
            step_text: Texte de l'etape (ex: "Transcription...", "Nettoyage...").
        """
        self.sig_update_step.emit(step_text)

    def show_preview(self, text: str) -> None:
        """Affiche un apercu de la transcription (thread-safe, auto-hide 3s).

        Args:
            text: Texte a afficher (tronque a 50 chars).
        """
        preview = text[:50] + "..." if len(text) > 50 else text
        self.sig_show_preview.emit(preview)

    def hide_widget(self) -> None:
        """Retourne a l'etat idle (retrocompatibilite)."""
        self.show_idle()

    # === Internal state handlers (main thread) ===

    @Slot()
    def _do_show_recording(self) -> None:
        """Passe en mode recording (main thread)."""
        self._state = "recording"
        self._run_js("setState('recording')")
        self._amplitude_timer.start()
        self.show()

    @Slot()
    def _do_show_processing(self) -> None:
        """Passe en mode processing (main thread)."""
        self._state = "processing"
        self._amplitude_timer.stop()
        self._run_js("setState('processing')")

    @Slot()
    def _do_show_idle(self) -> None:
        """Retourne a l'etat idle (main thread)."""
        self._state = "idle"
        self._amplitude_timer.stop()
        self._run_js("setState('idle')")

    @Slot()
    def _do_show_error(self) -> None:
        """Passe en mode error pendant 3s puis revient a idle (main thread)."""
        self._state = "error"
        self._amplitude_timer.stop()
        self._run_js("setState('error')")
        QTimer.singleShot(ERROR_DISPLAY_MS, self._do_show_idle)

    @Slot(str)
    def _do_update_step(self, step_text: str) -> None:
        """Met a jour l'indicateur d'etape (main thread)."""
        escaped = step_text.replace("'", "\\'")
        self._run_js(f"updateStep('{escaped}')")

    @Slot(str)
    def _do_show_preview(self, text: str) -> None:
        """Affiche un apercu de la transcription (main thread, auto-hide 3s)."""
        escaped = text.replace("'", "\\'").replace("\n", " ")
        self._run_js(f"showPreview('{escaped}')")

    def _send_amplitude(self) -> None:
        """Envoie l'amplitude audio courante au JS."""
        amplitude = 0.0
        if self._capture:
            amplitude = self._capture.current_amplitude
        normalized = min(1.0, amplitude * 4.0)
        self._run_js(f"updateAmplitude({normalized:.4f})")

    def _run_js(self, code: str) -> None:
        """Execute du JavaScript dans la page WebEngine.

        Args:
            code: Code JS a executer.
        """
        if self._web_view and self._web_view.page():
            self._web_view.page().runJavaScript(code)

    def set_capture(self, capture: object) -> None:
        """Definit l'instance AudioCapture pour la lecture d'amplitude.

        Args:
            capture: Instance AudioCapture.
        """
        self._capture = capture

    @property
    def state(self) -> str:
        """Retourne l'etat courant du widget."""
        return self._state
