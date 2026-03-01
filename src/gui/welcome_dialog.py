"""Welcome screen d'onboarding The Wave v2.1 (inspire de Wispr Flow)."""

import logging
import threading
from typing import Optional

from src.config.defaults import WHISPER_LANGUAGES

import numpy as np
import sounddevice as sd
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.gui.settings_dialog import HotkeyCapture
from src.utils.platform import resource_path

logger = logging.getLogger(__name__)

_TOTAL_PAGES = 8

# ====================================================================
# Traductions (en + fr, fallback anglais pour les autres)
# ====================================================================

_TRANSLATIONS = {
    "en": {
        # Step messages
        "step_messages": [
            "Let's go!",
            "What language?",
            "Good question...",
            "Almost ready!",
            "Let's check the sound...",
            "The moment of truth!",
            "Final touch...",
            "Congratulations!",
        ],
        "step_x_of_y": "Step {current} of {total}",
        # Page 0 - Welcome
        "welcome_title": "Welcome to The Wave",
        "welcome_subtitle": "Smart voice dictation — Speak, we write.",
        "welcome_bullet_1": "Press a shortcut, dictate, text appears",
        "welcome_bullet_2": "Automatic AI cleanup",
        "welcome_bullet_3": "Works in all your applications",
        "welcome_btn": "Get Started",
        # Page 1 - Language (always English)
        "lang_title": "Choose your language",
        "lang_subtitle": "This sets the language for the app interface and dictation.",
        "lang_hint": "You can change this anytime in Settings",
        # Page 2 - Motivation
        "motivation_title": "What brings you here?",
        "motivation_subtitle": "Select all that apply",
        "motiv_1_title": "I'm tired of typing all day",
        "motiv_1_desc": "Your fingers deserve a break",
        "motiv_2_title": "I want to write faster",
        "motiv_2_desc": "Dictate 4x faster than typing",
        "motiv_3_title": "I struggle to put ideas in writing",
        "motiv_3_desc": "Speaking is more natural",
        "motiv_4_title": "I want to dictate in all my apps",
        "motiv_4_desc": "Slack, Gmail, Word, everywhere",
        # Page 3 - Hotkey
        "hotkey_title": "Keyboard shortcut",
        "hotkey_desc": "Choose your shortcut to start/stop dictation.\nPress once to speak, once to stop.",
        "hotkey_hint": "Click in the field then press the desired key combination\n(e.g. F8, Ctrl+Shift+V, Alt+R)",
        # Page 4 - Mic
        "mic_title": "Microphone test",
        "mic_desc": "Let's check that your microphone works.",
        "mic_btn_test": "Test microphone",
        "mic_btn_listening": "Listening...",
        "mic_ok": "Microphone works!",
        "mic_fail": "No sound detected. Check your microphone.",
        "mic_error": "Cannot open microphone.",
        # Page 5 - Demo
        "demo_title": "Try it now!",
        "demo_subtitle": "Click Dictate, speak, and see the result",
        "demo_placeholder": "Your text will appear here...",
        "demo_btn_dictate": "Dictate",
        "demo_btn_stop": "Stop",
        "demo_status_speak": "Speak now...",
        "demo_status_transcribing": "Transcribing...",
        "demo_status_success": "Great! Your first dictation!",
        "demo_status_empty": "Empty text — try speaking louder",
        "demo_status_error": "Error — try again or skip",
        "demo_status_no_engine": "Engine not available — skip to next step",
        "demo_status_no_audio": "No audio captured",
        # Page 6 - Tone
        "tone_title": "How do you want to write?",
        "tone_subtitle": "Choose the cleanup style for your dictations",
        "tone_raw_title": "Raw",
        "tone_raw_desc": "No processing, exact transcription text",
        "tone_raw_example": '  "uh I think that like we should meet tomorrow"',
        "tone_auto_title": "Auto",
        "tone_auto_desc": "Detects the application and adapts automatically",
        "tone_auto_example": '  "I think we should meet tomorrow"',
        # Page 7 - Ready
        "ready_title": "All set!",
        "ready_subtitle": "You're ready to dictate 4x faster",
        "ready_mode_label": "Writing mode: {mode}",
        "ready_hint": "You can change settings anytime\nvia the icon in the taskbar (right-click).",
        "ready_btn": "Finish",
        # Mode names
        "mode_raw": "Raw",
        "mode_auto": "Auto",
        # Navigation
        "btn_previous": "Previous",
        "btn_next": "Next",
        "btn_skip": "Skip",
    },
    "fr": {
        "step_messages": [
            "C'est parti !",
            "Quelle langue ?",
            "Bonne question...",
            "Presque pret !",
            "Verifions le son...",
            "Le moment de verite !",
            "Derniere touche...",
            "Felicitations !",
        ],
        "step_x_of_y": "Etape {current} sur {total}",
        "welcome_title": "Bienvenue sur The Wave",
        "welcome_subtitle": "Dictee vocale intelligente — Parle, on ecrit.",
        "welcome_bullet_1": "Appuyez sur un raccourci, dictez, le texte apparait",
        "welcome_bullet_2": "Nettoyage automatique par IA",
        "welcome_bullet_3": "Fonctionne dans toutes vos applications",
        "welcome_btn": "Commencer",
        "lang_title": "Choose your language",
        "lang_subtitle": "This sets the language for the app interface and dictation.",
        "lang_hint": "You can change this anytime in Settings",
        "motivation_title": "Qu'est-ce qui vous amene ici ?",
        "motivation_subtitle": "Selectionnez tout ce qui vous correspond",
        "motiv_1_title": "J'en ai marre de taper toute la journee",
        "motiv_1_desc": "Vos doigts meritent une pause",
        "motiv_2_title": "Je veux ecrire plus vite",
        "motiv_2_desc": "Dictez 4x plus vite que le clavier",
        "motiv_3_title": "J'ai du mal a formuler mes idees par ecrit",
        "motiv_3_desc": "Parler, c'est plus naturel",
        "motiv_4_title": "Je veux dicter dans toutes mes apps",
        "motiv_4_desc": "Slack, Gmail, Word, partout",
        "hotkey_title": "Raccourci clavier",
        "hotkey_desc": "Choisissez votre raccourci pour demarrer/arreter la dictee.\nAppuyez une fois pour parler, une fois pour arreter.",
        "hotkey_hint": "Cliquez dans le champ puis appuyez sur la combinaison souhaitee\n(ex: F8, Ctrl+Shift+V, Alt+R)",
        "mic_title": "Test du microphone",
        "mic_desc": "Verifions que votre micro fonctionne.",
        "mic_btn_test": "Tester le micro",
        "mic_btn_listening": "Ecoute en cours...",
        "mic_ok": "Micro fonctionne !",
        "mic_fail": "Aucun son detecte. Verifiez votre micro.",
        "mic_error": "Impossible d'ouvrir le micro.",
        "demo_title": "Essayez maintenant !",
        "demo_subtitle": "Cliquez sur Dicter, parlez, et voyez le resultat",
        "demo_placeholder": "Votre texte apparaitra ici...",
        "demo_btn_dictate": "Dicter",
        "demo_btn_stop": "Arreter",
        "demo_status_speak": "Parlez maintenant...",
        "demo_status_transcribing": "Transcription en cours...",
        "demo_status_success": "Bravo ! Votre premiere dictee !",
        "demo_status_empty": "Texte vide — reessayez en parlant plus fort",
        "demo_status_error": "Erreur — reessayez ou passez",
        "demo_status_no_engine": "Moteur non disponible — passez a l'etape suivante",
        "demo_status_no_audio": "Aucun audio capture",
        "tone_title": "Comment voulez-vous ecrire ?",
        "tone_subtitle": "Choisissez le style de nettoyage de vos dictees",
        "tone_raw_title": "Brut",
        "tone_raw_desc": "Aucun traitement, texte exact de la transcription",
        "tone_raw_example": '  "euh je pense que du coup on devrait se voir demain"',
        "tone_auto_title": "Auto",
        "tone_auto_desc": "Détecte l'application et adapte automatiquement",
        "tone_auto_example": '  "je pense qu\'on devrait se voir demain"',
        "ready_title": "Tout est pret !",
        "ready_subtitle": "Vous etes pret a dicter 4x plus vite",
        "ready_mode_label": "Mode d'ecriture : {mode}",
        "ready_hint": "Vous pouvez modifier les parametres a tout moment\nvia l'icone dans la barre de taches (clic droit).",
        "ready_btn": "Terminer",
        "mode_raw": "Brut",
        "mode_auto": "Auto",
        "btn_previous": "Precedent",
        "btn_next": "Suivant",
        "btn_skip": "Passer",
    },
}


def _t(lang: str, key: str) -> str:
    """Retourne la traduction pour une cle dans la langue donnee."""
    translations = _TRANSLATIONS.get(lang, _TRANSLATIONS["en"])
    return translations.get(key, _TRANSLATIONS["en"].get(key, key))


# Style global du dialog
_STYLESHEET = """
QDialog {
    background-color: #18181b;
    color: #ffffff;
}
QLabel {
    color: #ffffff;
    background: transparent;
}
QLabel#subtitle {
    color: rgba(255, 255, 255, 0.6);
    font-size: 14px;
}
QLabel#bullet {
    color: rgba(255, 255, 255, 0.8);
    font-size: 13px;
}
QLabel#hint {
    color: rgba(255, 255, 255, 0.5);
    font-size: 12px;
}
QLabel#step-label {
    color: rgba(255, 255, 255, 0.4);
    font-size: 11px;
}
QLabel#encourage {
    color: #60a5fa;
    font-size: 12px;
    font-weight: 600;
}
QLabel#mic-ok {
    color: #4ade80;
    font-weight: bold;
    font-size: 14px;
}
QLabel#mic-fail {
    color: #f87171;
    font-weight: bold;
    font-size: 14px;
}
QLabel#hotkey-reminder {
    color: #60a5fa;
    font-size: 22px;
    font-weight: bold;
}
QLabel#mode-reminder {
    color: rgba(255, 255, 255, 0.7);
    font-size: 14px;
}
QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QPushButton:disabled {
    background-color: rgba(59, 130, 246, 0.3);
    color: rgba(255, 255, 255, 0.4);
}
QPushButton#secondary {
    background-color: transparent;
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: rgba(255, 255, 255, 0.7);
}
QPushButton#secondary:hover {
    border-color: rgba(255, 255, 255, 0.4);
    color: #ffffff;
}
QPushButton#mic-test {
    background-color: #22c55e;
}
QPushButton#mic-test:hover {
    background-color: #16a34a;
}
QPushButton#mic-test:disabled {
    background-color: rgba(34, 197, 94, 0.3);
}
QPushButton#dictate-btn {
    background-color: #8b5cf6;
    padding: 10px 32px;
    font-size: 15px;
}
QPushButton#dictate-btn:hover {
    background-color: #7c3aed;
}
QPushButton#skip-btn {
    background-color: transparent;
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: rgba(255, 255, 255, 0.5);
    font-size: 12px;
    padding: 6px 16px;
}
QPushButton#skip-btn:hover {
    color: rgba(255, 255, 255, 0.8);
    border-color: rgba(255, 255, 255, 0.3);
}
QProgressBar {
    background-color: rgba(255, 255, 255, 0.1);
    border: none;
    border-radius: 4px;
    height: 8px;
}
QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 4px;
}
QLineEdit {
    background-color: rgba(255, 255, 255, 0.1);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 16px;
    font-weight: bold;
}
QLineEdit:focus {
    border-color: #3b82f6;
}
QTextEdit {
    background-color: rgba(255, 255, 255, 0.05);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 12px;
    font-size: 14px;
}
"""


class _ProgressDots(QWidget):
    """Widget d'indicateur de progression avec dots et label."""

    def __init__(self, total: int = _TOTAL_PAGES, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._total = total
        self._current = 0
        self._lang = "en"
        self.setFixedHeight(40)

    def set_current(self, index: int) -> None:
        self._current = index
        self.update()

    def set_language(self, lang: str) -> None:
        self._lang = lang
        self.update()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        dot_radius = 5
        dot_spacing = 20
        total_width = self._total * dot_spacing
        start_x = (self.width() - total_width) // 2 + dot_spacing // 2

        for i in range(self._total):
            x = start_x + i * dot_spacing
            y = 12
            if i == self._current:
                painter.setBrush(QColor("#3b82f6"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(x - dot_radius, y - dot_radius, dot_radius * 2, dot_radius * 2)
            elif i < self._current:
                painter.setBrush(QColor("#3b82f6"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(x - 3, y - 3, 6, 6)
            else:
                painter.setBrush(QColor(255, 255, 255, 50))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(x - 3, y - 3, 6, 6)

        painter.setPen(QColor(255, 255, 255, 100))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        step_text = _t(self._lang, "step_x_of_y").format(
            current=self._current + 1, total=self._total,
        )
        painter.drawText(
            0, 28, self.width(), 14,
            Qt.AlignmentFlag.AlignCenter, step_text,
        )
        painter.end()


class _ClickableCard(QWidget):
    """Carte cliquable avec titre et description, rendu via paintEvent."""

    clicked = Signal()

    _COLOR_BG_NORMAL = QColor(255, 255, 255, 13)
    _COLOR_BG_HOVER = QColor(255, 255, 255, 25)
    _COLOR_BG_SELECTED = QColor(59, 130, 246, 38)
    _COLOR_BORDER_NORMAL = QColor(255, 255, 255, 25)
    _COLOR_BORDER_HOVER = QColor(255, 255, 255, 60)
    _COLOR_BORDER_SELECTED = QColor(59, 130, 246, 255)

    def __init__(self, title: str, description: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._selected = False
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        self._check_label = QLabel("")
        self._check_label.setFixedWidth(22)
        self._check_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._check_label.setStyleSheet("font-size: 16px; color: #3b82f6; background: transparent; border: none;")
        self._check_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._check_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        self._title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text_layout.addWidget(self._title_label)

        self._desc_label = None
        if description:
            self._desc_label = QLabel(description)
            self._desc_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px; background: transparent; border: none;")
            self._desc_label.setWordWrap(True)
            self._desc_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            text_layout.addWidget(self._desc_label)

        layout.addLayout(text_layout)

    def set_texts(self, title: str, description: str = "") -> None:
        """Met a jour le titre et la description."""
        self._title_label.setText(title)
        if self._desc_label and description:
            self._desc_label.setText(description)

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool) -> None:
        self._selected = value
        self._check_label.setText("\u2713" if value else "")
        self.update()

    def enterEvent(self, event: object) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        self._hovered = False
        self.update()

    def mousePressEvent(self, event: object) -> None:
        self.clicked.emit()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        if self._selected:
            bg, border = self._COLOR_BG_SELECTED, self._COLOR_BORDER_SELECTED
        elif self._hovered:
            bg, border = self._COLOR_BG_HOVER, self._COLOR_BORDER_HOVER
        else:
            bg, border = self._COLOR_BG_NORMAL, self._COLOR_BORDER_NORMAL
        painter.setBrush(bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 12, 12)
        painter.setPen(QPen(border, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 12, 12)
        painter.end()


class _TranscriptionWorker(QObject):
    """Worker pour la transcription dans un thread separe."""

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, audio_data: np.ndarray, engine: object, processor: object) -> None:
        super().__init__()
        self._audio = audio_data
        self._engine = engine
        self._processor = processor

    def run(self) -> None:
        try:
            prepared = self._processor.prepare_for_whisper(self._audio)
            text = self._engine.transcribe(prepared)
            self.finished.emit(text.strip() if text else "")
        except Exception as e:
            logger.error(f"Erreur transcription demo: {e}")
            self.error.emit(str(e))


class WelcomeDialog(QDialog):
    """Dialog d'onboarding multi-etapes pour le premier lancement (v2)."""

    def __init__(
        self,
        current_hotkey: str = "F8",
        engine: Optional[object] = None,
        processor: Optional[object] = None,
        feedback=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._hotkey = current_hotkey
        self._engine = engine
        self._processor = processor
        self._feedback = feedback
        self._cleaning_mode = "auto"
        self._language = "en"

        # Micro test state
        self._mic_stream: Optional[sd.InputStream] = None
        self._mic_timer: Optional[QTimer] = None
        self._mic_amplitude: float = 0.0
        self._mic_detected: bool = False

        # Demo state
        self._demo_recording: bool = False
        self._demo_audio_chunks: list = []
        self._demo_stream: Optional[sd.InputStream] = None
        self._demo_success: bool = False
        self._demo_worker_thread: Optional[threading.Thread] = None

        # Motivation selections
        self._motivation_selections: set = set()

        # Refs to translatable widgets (filled during build)
        self._i18n: dict = {}

        self._setup_window()
        self._build_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle("The Wave")
        self.setFixedSize(550, 500)
        self.setStyleSheet(_STYLESHEET)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._progress = _ProgressDots()
        layout.addWidget(self._progress)

        self._encourage_label = QLabel("")
        self._encourage_label.setObjectName("encourage")
        self._encourage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._encourage_label)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._stack.addWidget(self._build_page_welcome())      # 0
        self._stack.addWidget(self._build_page_language())      # 1
        self._stack.addWidget(self._build_page_motivation())    # 2
        self._stack.addWidget(self._build_page_hotkey())        # 3
        self._stack.addWidget(self._build_page_mic())           # 4
        self._stack.addWidget(self._build_page_demo())          # 5
        self._stack.addWidget(self._build_page_tone())          # 6
        self._stack.addWidget(self._build_page_ready())         # 7

        self._stack.setCurrentIndex(0)
        self._stack.currentChanged.connect(self._on_page_changed)

        # Apply initial language
        self._apply_language("en")

    def _go_to(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

    def _on_page_changed(self, index: int) -> None:
        self._progress.set_current(index)
        lang = self._language
        translations = _TRANSLATIONS.get(lang, _TRANSLATIONS["en"])
        step_messages = translations.get("step_messages", _TRANSLATIONS["en"]["step_messages"])
        if 0 <= index < len(step_messages):
            self._encourage_label.setText(step_messages[index])

        if index == 5:
            self._on_demo_page_entered()
        if index == 3:
            self._hotkey_next_btn.setEnabled(False)
            QTimer.singleShot(3000, lambda: self._hotkey_next_btn.setEnabled(True))
        if index == 7:
            self._hotkey_reminder.setText(f"{self._hotkey}")
            display_mode = self._cleaning_mode if self._cleaning_mode in ("raw", "auto") else "auto"
            mode_key = f"mode_{display_mode}"
            mode_text = _t(lang, mode_key)
            self._mode_reminder.setText(
                _t(lang, "ready_mode_label").format(mode=mode_text)
            )

    # ================================================================
    # Language system
    # ================================================================

    def _apply_language(self, lang: str) -> None:
        """Met a jour tous les textes de l'interface dans la langue choisie."""
        self._language = lang
        self._progress.set_language(lang)

        # Update all stored widget refs
        for key, widget in self._i18n.items():
            text = _t(lang, key)
            if isinstance(widget, QLabel):
                widget.setText(text)
            elif isinstance(widget, QPushButton):
                widget.setText(text)

        # Update motivation cards
        for i, card in enumerate(self._motivation_cards):
            card.set_texts(
                _t(lang, f"motiv_{i+1}_title"),
                _t(lang, f"motiv_{i+1}_desc"),
            )

        # Update tone cards + examples
        self._tone_cards["raw"].set_texts(
            _t(lang, "tone_raw_title"), _t(lang, "tone_raw_desc"),
        )
        self._tone_cards["auto"].set_texts(
            _t(lang, "tone_auto_title"), _t(lang, "tone_auto_desc"),
        )
        self._i18n_tone_raw_ex.setText(_t(lang, "tone_raw_example"))
        self._i18n_tone_auto_ex.setText(_t(lang, "tone_auto_example"))

        # Update demo placeholder
        self._demo_text.setPlaceholderText(_t(lang, "demo_placeholder"))

        # Update nav buttons on pages 3-7 (not registered via _reg to avoid key conflicts)
        prev_text = _t(lang, "btn_previous")
        next_text = _t(lang, "btn_next")
        skip_text = _t(lang, "btn_skip")
        for btn in [self._hotkey_prev_btn, self._mic_prev_btn, self._demo_prev_btn, self._tone_prev_btn]:
            btn.setText(prev_text)
        for btn in [self._hotkey_fwd_btn, self._mic_next_btn, self._demo_next_btn, self._tone_next_btn]:
            btn.setText(next_text)
        self._demo_skip_btn.setText(skip_text)

        # Update mic lang label
        _lang_names = {
            "en": "English", "fr": "Francais", "es": "Espanol",
            "de": "Deutsch", "it": "Italiano", "pt": "Portugues",
            "nl": "Nederlands", "ja": "Japanese", "ko": "Korean",
            "zh": "Chinese", "ru": "Russian", "ar": "Arabic",
            "tr": "Turkish", "pl": "Polish", "sv": "Swedish",
        }
        lang_display = _lang_names.get(lang, lang)
        self._mic_lang_label.setText(f"\U0001f399 Dictation language: {lang_display}")

        # Force repaint progress dots
        self._progress.update()

        # Update current encourage label
        idx = self._stack.currentIndex()
        translations = _TRANSLATIONS.get(lang, _TRANSLATIONS["en"])
        step_messages = translations.get("step_messages", _TRANSLATIONS["en"]["step_messages"])
        if 0 <= idx < len(step_messages):
            self._encourage_label.setText(step_messages[idx])

    def _reg(self, key: str, widget: object) -> object:
        """Enregistre un widget pour la traduction automatique."""
        self._i18n[key] = widget
        return widget

    # ================================================================
    # Page 0 : Welcome
    # ================================================================

    def _build_page_welcome(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 30)
        layout.setSpacing(12)

        import os
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = resource_path(os.path.join("src", "gui", "orb", "logo.png"))
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            logo_label.setPixmap(
                pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        layout.addWidget(logo_label)

        title = self._reg("welcome_title", QLabel(""))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = self._reg("welcome_subtitle", QLabel(""))
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        self._welcome_bullet_1 = self._reg("welcome_bullet_1", QLabel(""))
        self._welcome_bullet_1.setObjectName("bullet")
        layout.addWidget(self._welcome_bullet_1)
        self._welcome_bullet_2 = self._reg("welcome_bullet_2", QLabel(""))
        self._welcome_bullet_2.setObjectName("bullet")
        layout.addWidget(self._welcome_bullet_2)
        self._welcome_bullet_3 = self._reg("welcome_bullet_3", QLabel(""))
        self._welcome_bullet_3.setObjectName("bullet")
        layout.addWidget(self._welcome_bullet_3)

        layout.addStretch()

        btn = self._reg("welcome_btn", QPushButton(""))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self._go_to(1))
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    # ================================================================
    # Page 1 : Language (always English — first page)
    # ================================================================

    def _build_page_language(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 30)
        layout.setSpacing(16)

        title = QLabel("Choose your language")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = QLabel("This sets the language for the app interface and dictation.")
        desc.setObjectName("subtitle")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(20)

        self._lang_combo = QComboBox()
        self._lang_combo.setStyleSheet(
            "QComboBox { background-color: rgba(255,255,255,0.08); color: #ffffff; "
            "border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; padding: 10px 14px; "
            "font-size: 14px; min-width: 250px; }"
            "QComboBox:hover { border-color: rgba(255,255,255,0.4); }"
            "QComboBox::drop-down { border: none; width: 24px; }"
            "QComboBox::down-arrow { image: none; border-left: 4px solid transparent; "
            "border-right: 4px solid transparent; border-top: 5px solid rgba(255,255,255,0.5); margin-right: 8px; }"
            "QComboBox QAbstractItemView { background-color: #27272a; color: #ffffff; "
            "border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; "
            "selection-background-color: rgba(59,130,246,0.3); padding: 4px; }"
        )
        self._lang_combo.addItem("🌐 Auto-detect", "auto")
        for code, name in WHISPER_LANGUAGES:
            self._lang_combo.addItem(f"{name} ({code})", code)
        self._lang_combo.setCurrentIndex(0)
        layout.addWidget(self._lang_combo, alignment=Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("You can change this anytime in Settings")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()

        nav = QHBoxLayout()
        btn_prev = QPushButton("Previous")
        btn_prev.setObjectName("secondary")
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.clicked.connect(lambda: self._go_to(0))
        nav.addWidget(btn_prev)
        nav.addStretch()

        btn_next = QPushButton("Next")
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.clicked.connect(self._go_to_motivation_from_language)
        nav.addWidget(btn_next)

        layout.addLayout(nav)
        return page

    def _go_to_motivation_from_language(self) -> None:
        self._language = self._lang_combo.currentData()
        self._apply_language(self._language)
        self._go_to(2)

    # ================================================================
    # Page 2 : Motivation
    # ================================================================

    def _build_page_motivation(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 10, 40, 30)
        layout.setSpacing(10)

        title = self._reg("motivation_title", QLabel(""))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(17)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = self._reg("motivation_subtitle", QLabel(""))
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        self._motivation_cards: list[_ClickableCard] = []
        for i in range(4):
            card = _ClickableCard("", "")
            card.clicked.connect(lambda idx=i: self._toggle_motivation(idx))
            self._motivation_cards.append(card)
            layout.addWidget(card)

        layout.addStretch()

        nav = QHBoxLayout()
        btn_prev = self._reg("btn_previous", QPushButton(""))
        btn_prev.setObjectName("secondary")
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.clicked.connect(lambda: self._go_to(1))
        nav.addWidget(btn_prev)
        nav.addStretch()

        self._motivation_next_btn = self._reg("btn_next", QPushButton(""))
        self._motivation_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._motivation_next_btn.setEnabled(False)
        self._motivation_next_btn.clicked.connect(lambda: self._go_to(3))
        nav.addWidget(self._motivation_next_btn)

        layout.addLayout(nav)
        return page

    def _toggle_motivation(self, index: int) -> None:
        card = self._motivation_cards[index]
        if index in self._motivation_selections:
            self._motivation_selections.discard(index)
            card.selected = False
        else:
            self._motivation_selections.add(index)
            card.selected = True
        self._motivation_next_btn.setEnabled(len(self._motivation_selections) > 0)

    # ================================================================
    # Page 3 : Hotkey
    # ================================================================

    def _build_page_hotkey(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 30)
        layout.setSpacing(16)

        title = self._reg("hotkey_title", QLabel(""))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = self._reg("hotkey_desc", QLabel(""))
        desc.setObjectName("subtitle")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(20)

        self._hotkey_capture = HotkeyCapture(self._hotkey)
        self._hotkey_capture.setMinimumHeight(44)
        self._hotkey_capture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hotkey_capture)

        hint = self._reg("hotkey_hint", QLabel(""))
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()

        nav = QHBoxLayout()
        btn_prev = QPushButton("")
        btn_prev.setObjectName("secondary")
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.clicked.connect(lambda: self._go_to(2))
        nav.addWidget(btn_prev)
        nav.addStretch()

        self._hotkey_next_btn = QPushButton("")
        self._hotkey_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hotkey_next_btn.clicked.connect(self._go_to_mic_from_hotkey)
        nav.addWidget(self._hotkey_next_btn)

        # These share keys with motivation nav, store separately
        self._hotkey_prev_btn = btn_prev
        self._hotkey_fwd_btn = self._hotkey_next_btn

        layout.addLayout(nav)
        return page

    def _go_to_mic_from_hotkey(self) -> None:
        self._hotkey = self._hotkey_capture.captured_hotkey
        self._go_to(4)

    # ================================================================
    # Page 4 : Mic test
    # ================================================================

    def _build_page_mic(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 30)
        layout.setSpacing(16)

        title = self._reg("mic_title", QLabel(""))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = self._reg("mic_desc", QLabel(""))
        desc.setObjectName("subtitle")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(10)

        self._volume_bar = QProgressBar()
        self._volume_bar.setMinimum(0)
        self._volume_bar.setMaximum(100)
        self._volume_bar.setValue(0)
        self._volume_bar.setTextVisible(False)
        self._volume_bar.setFixedHeight(12)
        layout.addWidget(self._volume_bar)

        self._mic_status = QLabel("")
        self._mic_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._mic_status)

        layout.addSpacing(10)

        self._mic_lang_label = QLabel("")
        self._mic_lang_label.setObjectName("hint")
        self._mic_lang_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._mic_lang_label)

        self._mic_btn = self._reg("mic_btn_test", QPushButton(""))
        self._mic_btn.setObjectName("mic-test")
        self._mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mic_btn.clicked.connect(self._start_mic_test)
        layout.addWidget(self._mic_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        nav = QHBoxLayout()
        self._mic_prev_btn = QPushButton("")
        self._mic_prev_btn.setObjectName("secondary")
        self._mic_prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mic_prev_btn.clicked.connect(lambda: self._go_to(3))
        nav.addWidget(self._mic_prev_btn)
        nav.addStretch()

        self._mic_next_btn = QPushButton("")
        self._mic_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mic_next_btn.clicked.connect(lambda: self._go_to(5))
        nav.addWidget(self._mic_next_btn)

        layout.addLayout(nav)
        return page

    def _start_mic_test(self) -> None:
        lang = self._language
        self._mic_btn.setEnabled(False)
        self._mic_btn.setText(_t(lang, "mic_btn_listening"))
        self._mic_status.setText("")
        self._mic_status.setStyleSheet("")
        self._mic_detected = False
        self._mic_amplitude = 0.0
        self._volume_bar.setValue(0)

        try:
            self._mic_stream = sd.InputStream(
                samplerate=16000, channels=1, dtype="float32",
                blocksize=1024, callback=self._mic_callback,
            )
            self._mic_stream.start()
            if self._feedback:
                self._feedback.play_start()
        except Exception as e:
            logger.error(f"Erreur ouverture micro: {e}")
            self._mic_status.setStyleSheet("color: #f87171; font-weight: bold; font-size: 14px;")
            self._mic_status.setText(_t(lang, "mic_error"))
            self._mic_btn.setEnabled(True)
            self._mic_btn.setText(_t(lang, "mic_btn_test"))
            return

        self._mic_timer = QTimer(self)
        self._mic_timer.setInterval(50)
        self._mic_timer.timeout.connect(self._update_volume_bar)
        self._mic_timer.start()
        QTimer.singleShot(3000, self._stop_mic_test)

    def _mic_callback(self, indata: np.ndarray, frames: int, time_info: object, status: object) -> None:
        amp = float(np.abs(indata).mean())
        self._mic_amplitude = amp
        if amp > 0.005:
            self._mic_detected = True

    @Slot()
    def _update_volume_bar(self) -> None:
        value = int(min(100, self._mic_amplitude * 500))
        self._volume_bar.setValue(value)

    def _stop_mic_test(self) -> None:
        lang = self._language
        if self._mic_timer:
            self._mic_timer.stop()
            self._mic_timer = None
        if self._feedback:
            self._feedback.play_stop()
        if self._mic_stream:
            try:
                self._mic_stream.stop()
                self._mic_stream.close()
            except Exception:
                pass
            self._mic_stream = None

        self._volume_bar.setValue(0)
        self._mic_btn.setEnabled(True)
        self._mic_btn.setText(_t(lang, "mic_btn_test"))

        if self._mic_detected:
            self._mic_status.setStyleSheet("color: #4ade80; font-weight: bold; font-size: 14px;")
            self._mic_status.setText(_t(lang, "mic_ok"))
        else:
            self._mic_status.setStyleSheet("color: #f87171; font-weight: bold; font-size: 14px;")
            self._mic_status.setText(_t(lang, "mic_fail"))

    # ================================================================
    # Page 5 : Demo
    # ================================================================

    def _build_page_demo(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 10, 40, 30)
        layout.setSpacing(12)

        title = self._reg("demo_title", QLabel(""))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = self._reg("demo_subtitle", QLabel(""))
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        self._demo_text = QTextEdit()
        self._demo_text.setReadOnly(True)
        self._demo_text.setPlaceholderText("")
        self._demo_text.setMinimumHeight(100)
        self._demo_text.setMaximumHeight(140)
        layout.addWidget(self._demo_text)

        self._demo_btn = self._reg("demo_btn_dictate", QPushButton(""))
        self._demo_btn.setObjectName("dictate-btn")
        self._demo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._demo_btn.clicked.connect(self._toggle_demo_recording)
        layout.addWidget(self._demo_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._demo_status = QLabel("")
        self._demo_status.setObjectName("hint")
        self._demo_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._demo_status)

        layout.addStretch()

        nav = QHBoxLayout()
        self._demo_prev_btn = QPushButton("")
        self._demo_prev_btn.setObjectName("secondary")
        self._demo_prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._demo_prev_btn.clicked.connect(lambda: self._go_to(4))
        nav.addWidget(self._demo_prev_btn)
        nav.addStretch()

        self._demo_skip_btn = self._reg("btn_skip", QPushButton(""))
        self._demo_skip_btn.setObjectName("skip-btn")
        self._demo_skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._demo_skip_btn.setVisible(False)
        self._demo_skip_btn.clicked.connect(lambda: self._go_to(6))
        nav.addWidget(self._demo_skip_btn)

        self._demo_next_btn = QPushButton("")
        self._demo_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._demo_next_btn.setEnabled(False)
        self._demo_next_btn.clicked.connect(lambda: self._go_to(6))
        nav.addWidget(self._demo_next_btn)

        layout.addLayout(nav)
        return page

    def _on_demo_page_entered(self) -> None:
        if not self._demo_success:
            QTimer.singleShot(10000, self._show_demo_skip)

    def _show_demo_skip(self) -> None:
        if self._stack.currentIndex() == 5 and not self._demo_success:
            self._demo_skip_btn.setVisible(True)

    def _toggle_demo_recording(self) -> None:
        if self._demo_recording:
            self._stop_demo_recording()
        else:
            self._start_demo_recording()

    def _start_demo_recording(self) -> None:
        lang = self._language
        self._demo_audio_chunks = []
        self._demo_recording = True
        self._demo_btn.setText(_t(lang, "demo_btn_stop"))
        self._demo_btn.setStyleSheet("background-color: #ef4444;")
        self._demo_status.setText(_t(lang, "demo_status_speak"))
        self._demo_text.setPlainText("")

        try:
            self._demo_stream = sd.InputStream(
                samplerate=16000, channels=1, dtype="float32",
                blocksize=1024, callback=self._demo_audio_callback,
            )
            self._demo_stream.start()
        except Exception as e:
            logger.error(f"Erreur ouverture micro demo: {e}")
            self._demo_status.setText(_t(lang, "mic_error"))
            self._demo_recording = False
            self._demo_btn.setText(_t(lang, "demo_btn_dictate"))
            self._demo_btn.setStyleSheet("")

    def _demo_audio_callback(self, indata: np.ndarray, frames: int, time_info: object, status: object) -> None:
        self._demo_audio_chunks.append(indata.copy())

    def _stop_demo_recording(self) -> None:
        lang = self._language
        self._demo_recording = False
        self._demo_btn.setText(_t(lang, "demo_btn_dictate"))
        self._demo_btn.setStyleSheet("")

        if self._demo_stream:
            try:
                self._demo_stream.stop()
                self._demo_stream.close()
            except Exception:
                pass
            self._demo_stream = None

        if not self._demo_audio_chunks:
            self._demo_status.setText(_t(lang, "demo_status_no_audio"))
            return

        audio = np.concatenate(self._demo_audio_chunks, axis=0).flatten()

        if self._engine and self._processor:
            self._demo_btn.setEnabled(False)
            self._demo_status.setText(_t(lang, "demo_status_transcribing"))
            self._demo_worker = _TranscriptionWorker(audio, self._engine, self._processor)
            self._demo_worker.finished.connect(self._on_demo_transcription_done)
            self._demo_worker.error.connect(self._on_demo_transcription_error)
            self._demo_worker_thread = threading.Thread(target=self._demo_worker.run, daemon=True)
            self._demo_worker_thread.start()
        else:
            self._demo_status.setText(_t(lang, "demo_status_no_engine"))
            self._demo_skip_btn.setVisible(True)

    @Slot(str)
    def _on_demo_transcription_done(self, text: str) -> None:
        lang = self._language
        self._demo_btn.setEnabled(True)
        if text:
            self._demo_text.setPlainText(text)
            self._demo_status.setText(_t(lang, "demo_status_success"))
            self._demo_success = True
            self._demo_next_btn.setEnabled(True)
        else:
            self._demo_status.setText(_t(lang, "demo_status_empty"))

    @Slot(str)
    def _on_demo_transcription_error(self, error: str) -> None:
        lang = self._language
        self._demo_btn.setEnabled(True)
        self._demo_status.setText(_t(lang, "demo_status_error"))
        self._demo_skip_btn.setVisible(True)
        logger.error(f"Demo transcription error: {error}")

    # ================================================================
    # Page 6 : Tone
    # ================================================================

    def _build_page_tone(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 10, 40, 30)
        layout.setSpacing(12)

        title = self._reg("tone_title", QLabel(""))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = self._reg("tone_subtitle", QLabel(""))
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(6)

        raw_card = _ClickableCard("", "")
        raw_card.clicked.connect(lambda: self._select_tone("raw"))
        layout.addWidget(raw_card)

        self._i18n_tone_raw_ex = QLabel("")
        self._i18n_tone_raw_ex.setObjectName("hint")
        self._i18n_tone_raw_ex.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 11px; margin-left: 16px;")
        layout.addWidget(self._i18n_tone_raw_ex)

        layout.addSpacing(4)

        auto_card = _ClickableCard("", "")
        auto_card.clicked.connect(lambda: self._select_tone("auto"))
        layout.addWidget(auto_card)

        self._i18n_tone_auto_ex = QLabel("")
        self._i18n_tone_auto_ex.setObjectName("hint")
        self._i18n_tone_auto_ex.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 11px; margin-left: 16px;")
        layout.addWidget(self._i18n_tone_auto_ex)

        self._tone_cards = {"raw": raw_card, "auto": auto_card}
        auto_card.selected = True

        layout.addStretch()

        nav = QHBoxLayout()
        self._tone_prev_btn = QPushButton("")
        self._tone_prev_btn.setObjectName("secondary")
        self._tone_prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tone_prev_btn.clicked.connect(lambda: self._go_to(5))
        nav.addWidget(self._tone_prev_btn)
        nav.addStretch()

        self._tone_next_btn = QPushButton("")
        self._tone_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tone_next_btn.clicked.connect(lambda: self._go_to(7))
        nav.addWidget(self._tone_next_btn)

        layout.addLayout(nav)
        return page

    def _select_tone(self, mode: str) -> None:
        self._cleaning_mode = mode
        for key, card in self._tone_cards.items():
            card.selected = (key == mode)

    # ================================================================
    # Page 7 : Ready
    # ================================================================

    def _build_page_ready(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 30)
        layout.setSpacing(16)

        layout.addStretch()

        title = self._reg("ready_title", QLabel(""))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        encourage = self._reg("ready_subtitle", QLabel(""))
        encourage.setObjectName("subtitle")
        encourage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(encourage)

        layout.addSpacing(10)

        self._hotkey_reminder = QLabel()
        self._hotkey_reminder.setObjectName("hotkey-reminder")
        self._hotkey_reminder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hotkey_reminder)

        self._mode_reminder = QLabel()
        self._mode_reminder.setObjectName("mode-reminder")
        self._mode_reminder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._mode_reminder)

        layout.addSpacing(10)

        hint = self._reg("ready_hint", QLabel(""))
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()

        btn = self._reg("ready_btn", QPushButton(""))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    # ================================================================
    # Properties
    # ================================================================

    @property
    def hotkey(self) -> str:
        return self._hotkey

    @property
    def cleaning_mode(self) -> str:
        return self._cleaning_mode

    @property
    def language(self) -> str:
        return self._language

    def closeEvent(self, event: object) -> None:
        self._stop_mic_test()
        if self._demo_stream:
            try:
                self._demo_stream.stop()
                self._demo_stream.close()
            except Exception:
                pass
            self._demo_stream = None
        super().closeEvent(event)
