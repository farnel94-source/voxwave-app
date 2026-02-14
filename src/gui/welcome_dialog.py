"""Welcome screen d'onboarding VoxTool v2 (inspire de Wispr Flow)."""

import logging
import threading
from typing import Optional

import numpy as np
import sounddevice as sd
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen
from PySide6.QtWidgets import (
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

_TOTAL_PAGES = 7

# Messages encourageants par etape
_STEP_MESSAGES = [
    "C'est parti !",
    "Bonne question...",
    "Presque pret !",
    "Verifions le son...",
    "Le moment de verite !",
    "Derniere touche...",
    "Felicitations !",
]

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

# Les cartes utilisent paintEvent pour le rendu (pas de stylesheet cascade)


class _ProgressDots(QWidget):
    """Widget d'indicateur de progression avec dots et label."""

    def __init__(self, total: int = _TOTAL_PAGES, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._total = total
        self._current = 0
        self.setFixedHeight(40)

    def set_current(self, index: int) -> None:
        """Met a jour le dot actif."""
        self._current = index
        self.update()

    def paintEvent(self, event: object) -> None:
        """Dessine les dots de progression."""
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

        # Texte etape
        painter.setPen(QColor(255, 255, 255, 100))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(
            0, 28, self.width(), 14,
            Qt.AlignmentFlag.AlignCenter,
            f"Etape {self._current + 1} sur {self._total}",
        )
        painter.end()


class _ClickableCard(QWidget):
    """Carte cliquable avec titre et description, rendu via paintEvent."""

    clicked = Signal()

    _COLOR_BG_NORMAL = QColor(255, 255, 255, 13)       # rgba(255,255,255,0.05)
    _COLOR_BG_HOVER = QColor(255, 255, 255, 25)        # rgba(255,255,255,0.10)
    _COLOR_BG_SELECTED = QColor(59, 130, 246, 38)      # rgba(59,130,246,0.15)
    _COLOR_BORDER_NORMAL = QColor(255, 255, 255, 25)   # rgba(255,255,255,0.10)
    _COLOR_BORDER_HOVER = QColor(255, 255, 255, 60)    # rgba(255,255,255,0.24)
    _COLOR_BORDER_SELECTED = QColor(59, 130, 246, 255) # #3b82f6

    def __init__(
        self,
        title: str,
        description: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._selected = False
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        # Checkmark indicator
        self._check_label = QLabel("")
        self._check_label.setFixedWidth(22)
        self._check_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._check_label.setStyleSheet("font-size: 16px; color: #3b82f6; background: transparent; border: none;")
        self._check_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._check_label)

        # Textes
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

        if description:
            self._desc_label = QLabel(description)
            self._desc_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px; background: transparent; border: none;")
            self._desc_label.setWordWrap(True)
            self._desc_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            text_layout.addWidget(self._desc_label)

        layout.addLayout(text_layout)

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
        """Dessine le fond et la bordure de la carte."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)

        # Couleurs selon l'etat
        if self._selected:
            bg = self._COLOR_BG_SELECTED
            border = self._COLOR_BORDER_SELECTED
        elif self._hovered:
            bg = self._COLOR_BG_HOVER
            border = self._COLOR_BORDER_HOVER
        else:
            bg = self._COLOR_BG_NORMAL
            border = self._COLOR_BORDER_NORMAL

        # Fond
        painter.setBrush(bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 12, 12)

        # Bordure
        pen = QPen(border, 2)
        painter.setPen(pen)
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
        """Execute la transcription."""
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
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._hotkey = current_hotkey
        self._engine = engine
        self._processor = processor
        self._cleaning_mode = "verbatim"

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

        self._setup_window()
        self._build_ui()

    def _setup_window(self) -> None:
        """Configure la fenetre du dialog."""
        self.setWindowTitle("VoxTool")
        self.setFixedSize(550, 500)
        self.setStyleSheet(_STYLESHEET)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )

    def _build_ui(self) -> None:
        """Construit l'interface avec QStackedWidget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Progress dots en haut
        self._progress = _ProgressDots()
        layout.addWidget(self._progress)

        # Encourage label
        self._encourage_label = QLabel(_STEP_MESSAGES[0])
        self._encourage_label.setObjectName("encourage")
        self._encourage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._encourage_label)

        # Stack
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._stack.addWidget(self._build_page_welcome())      # 0
        self._stack.addWidget(self._build_page_motivation())    # 1
        self._stack.addWidget(self._build_page_hotkey())        # 2
        self._stack.addWidget(self._build_page_mic())           # 3
        self._stack.addWidget(self._build_page_demo())          # 4
        self._stack.addWidget(self._build_page_tone())          # 5
        self._stack.addWidget(self._build_page_ready())         # 6

        self._stack.setCurrentIndex(0)
        self._stack.currentChanged.connect(self._on_page_changed)

    def _go_to(self, index: int) -> None:
        """Navigue vers une page."""
        self._stack.setCurrentIndex(index)

    def _on_page_changed(self, index: int) -> None:
        """Met a jour la progression et le contenu dynamique."""
        self._progress.set_current(index)
        if 0 <= index < len(_STEP_MESSAGES):
            self._encourage_label.setText(_STEP_MESSAGES[index])

        # Page demo : demarrer le timer pour le bouton Passer
        if index == 4:
            self._on_demo_page_entered()

        # Page hotkey : desactiver Suivant pendant 3s (no-skip)
        if index == 2:
            self._hotkey_next_btn.setEnabled(False)
            QTimer.singleShot(3000, lambda: self._hotkey_next_btn.setEnabled(True))

        # Page ready : maj contenu dynamique
        if index == 6:
            self._hotkey_reminder.setText(f"{self._hotkey}")
            mode_text = "Naturel" if self._cleaning_mode == "verbatim" else "Professionnel"
            self._mode_reminder.setText(f"Mode d'ecriture : {mode_text}")

    # ================================================================
    # Page 0 : Bienvenue
    # ================================================================

    def _build_page_welcome(self) -> QWidget:
        """Construit la page de bienvenue."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 30)
        layout.setSpacing(12)

        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        import os
        logo_path = resource_path(os.path.join("src", "gui", "orb", "logo.png"))
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            logo_label.setPixmap(
                pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        layout.addWidget(logo_label)

        # Titre
        title = QLabel("Bienvenue sur VoxTool")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Sous-titre
        subtitle = QLabel("Dictee vocale intelligente — Parle, on ecrit.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # Bullet points
        bullets = [
            "Appuyez sur un raccourci, dictez, le texte apparait",
            "Nettoyage automatique par IA",
            "Fonctionne dans toutes vos applications",
        ]
        for text in bullets:
            bullet = QLabel(f"  \u2022  {text}")
            bullet.setObjectName("bullet")
            layout.addWidget(bullet)

        layout.addStretch()

        # Bouton Commencer
        btn = QPushButton("Commencer")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self._go_to(1))
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    # ================================================================
    # Page 1 : Pourquoi VoxTool ?
    # ================================================================

    def _build_page_motivation(self) -> QWidget:
        """Construit la page de motivation / besoins."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 10, 40, 30)
        layout.setSpacing(10)

        title = QLabel("Qu'est-ce qui vous amene ici ?")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(17)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel("Selectionnez tout ce qui vous correspond")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # 4 cartes cliquables (multi-select)
        motivations = [
            ("J'en ai marre de taper toute la journee", "Vos doigts meritent une pause"),
            ("Je veux ecrire plus vite", "Dictez 4x plus vite que le clavier"),
            ("J'ai du mal a formuler mes idees par ecrit", "Parler, c'est plus naturel"),
            ("Je veux dicter dans toutes mes apps", "Slack, Gmail, Word, partout"),
        ]

        self._motivation_cards: list[_ClickableCard] = []
        for i, (title_text, desc_text) in enumerate(motivations):
            card = _ClickableCard(title_text, desc_text)
            card.clicked.connect(lambda idx=i: self._toggle_motivation(idx))
            self._motivation_cards.append(card)
            layout.addWidget(card)

        layout.addStretch()

        # Navigation
        nav = QHBoxLayout()
        btn_prev = QPushButton("Precedent")
        btn_prev.setObjectName("secondary")
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.clicked.connect(lambda: self._go_to(0))
        nav.addWidget(btn_prev)
        nav.addStretch()

        self._motivation_next_btn = QPushButton("Suivant")
        self._motivation_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._motivation_next_btn.setEnabled(False)
        self._motivation_next_btn.clicked.connect(lambda: self._go_to(2))
        nav.addWidget(self._motivation_next_btn)

        layout.addLayout(nav)
        return page

    def _toggle_motivation(self, index: int) -> None:
        """Toggle une selection de motivation."""
        card = self._motivation_cards[index]
        if index in self._motivation_selections:
            self._motivation_selections.discard(index)
            card.selected = False
        else:
            self._motivation_selections.add(index)
            card.selected = True

        # Activer Suivant si au moins 1 selection
        self._motivation_next_btn.setEnabled(len(self._motivation_selections) > 0)

    # ================================================================
    # Page 2 : Raccourci clavier (no-skip 3s)
    # ================================================================

    def _build_page_hotkey(self) -> QWidget:
        """Construit la page de configuration du raccourci."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 30)
        layout.setSpacing(16)

        title = QLabel("Raccourci clavier")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = QLabel("Choisissez votre raccourci pour demarrer/arreter la dictee.\nAppuyez une fois pour parler, une fois pour arreter.")
        desc.setObjectName("subtitle")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(20)

        # HotkeyCapture
        self._hotkey_capture = HotkeyCapture(self._hotkey)
        self._hotkey_capture.setMinimumHeight(44)
        self._hotkey_capture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hotkey_capture)

        hint = QLabel("Cliquez dans le champ puis appuyez sur la combinaison souhaitee\n(ex: F8, Ctrl+Shift+V, Alt+R)")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()

        # Navigation
        nav = QHBoxLayout()
        btn_prev = QPushButton("Precedent")
        btn_prev.setObjectName("secondary")
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.clicked.connect(lambda: self._go_to(1))
        nav.addWidget(btn_prev)
        nav.addStretch()

        self._hotkey_next_btn = QPushButton("Suivant")
        self._hotkey_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hotkey_next_btn.clicked.connect(self._go_to_mic_page)
        nav.addWidget(self._hotkey_next_btn)

        layout.addLayout(nav)
        return page

    def _go_to_mic_page(self) -> None:
        """Passe a la page micro en sauvegardant le hotkey."""
        self._hotkey = self._hotkey_capture.captured_hotkey
        self._go_to(3)

    # ================================================================
    # Page 3 : Test micro
    # ================================================================

    def _build_page_mic(self) -> QWidget:
        """Construit la page de test du microphone."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 30)
        layout.setSpacing(16)

        title = QLabel("Test du microphone")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = QLabel("Verifions que votre micro fonctionne.")
        desc.setObjectName("subtitle")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(10)

        # Barre de volume
        self._volume_bar = QProgressBar()
        self._volume_bar.setMinimum(0)
        self._volume_bar.setMaximum(100)
        self._volume_bar.setValue(0)
        self._volume_bar.setTextVisible(False)
        self._volume_bar.setFixedHeight(12)
        layout.addWidget(self._volume_bar)

        # Statut micro
        self._mic_status = QLabel("")
        self._mic_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._mic_status)

        layout.addSpacing(10)

        # Bouton test
        self._mic_btn = QPushButton("Tester le micro")
        self._mic_btn.setObjectName("mic-test")
        self._mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mic_btn.clicked.connect(self._start_mic_test)
        layout.addWidget(self._mic_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        # Navigation
        nav = QHBoxLayout()
        btn_prev = QPushButton("Precedent")
        btn_prev.setObjectName("secondary")
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.clicked.connect(lambda: self._go_to(2))
        nav.addWidget(btn_prev)
        nav.addStretch()

        btn_next = QPushButton("Suivant")
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.clicked.connect(lambda: self._go_to(4))
        nav.addWidget(btn_next)

        layout.addLayout(nav)
        return page

    def _start_mic_test(self) -> None:
        """Lance un test micro de 3 secondes."""
        self._mic_btn.setEnabled(False)
        self._mic_btn.setText("Ecoute en cours...")
        self._mic_status.setText("")
        self._mic_status.setObjectName("")
        self._mic_status.setStyleSheet("")
        self._mic_detected = False
        self._mic_amplitude = 0.0
        self._volume_bar.setValue(0)

        try:
            self._mic_stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="float32",
                blocksize=1024,
                callback=self._mic_callback,
            )
            self._mic_stream.start()
        except Exception as e:
            logger.error(f"Erreur ouverture micro: {e}")
            self._mic_status.setObjectName("mic-fail")
            self._mic_status.setStyleSheet("color: #f87171; font-weight: bold; font-size: 14px;")
            self._mic_status.setText("Impossible d'ouvrir le micro.")
            self._mic_btn.setEnabled(True)
            self._mic_btn.setText("Tester le micro")
            return

        self._mic_timer = QTimer(self)
        self._mic_timer.setInterval(50)
        self._mic_timer.timeout.connect(self._update_volume_bar)
        self._mic_timer.start()

        QTimer.singleShot(3000, self._stop_mic_test)

    def _mic_callback(self, indata: np.ndarray, frames: int, time_info: object, status: object) -> None:
        """Callback sounddevice pour mesurer l'amplitude."""
        amp = float(np.abs(indata).mean())
        self._mic_amplitude = amp
        if amp > 0.005:
            self._mic_detected = True

    @Slot()
    def _update_volume_bar(self) -> None:
        """Met a jour la barre de progression avec l'amplitude courante."""
        value = int(min(100, self._mic_amplitude * 500))
        self._volume_bar.setValue(value)

    def _stop_mic_test(self) -> None:
        """Arrete le test micro et affiche le resultat."""
        if self._mic_timer:
            self._mic_timer.stop()
            self._mic_timer = None

        if self._mic_stream:
            try:
                self._mic_stream.stop()
                self._mic_stream.close()
            except Exception:
                pass
            self._mic_stream = None

        self._volume_bar.setValue(0)
        self._mic_btn.setEnabled(True)
        self._mic_btn.setText("Tester le micro")

        if self._mic_detected:
            self._mic_status.setObjectName("mic-ok")
            self._mic_status.setStyleSheet("color: #4ade80; font-weight: bold; font-size: 14px;")
            self._mic_status.setText("Micro fonctionne !")
        else:
            self._mic_status.setObjectName("mic-fail")
            self._mic_status.setStyleSheet("color: #f87171; font-weight: bold; font-size: 14px;")
            self._mic_status.setText("Aucun son detecte. Verifiez votre micro.")

    # ================================================================
    # Page 4 : Demo interactive
    # ================================================================

    def _build_page_demo(self) -> QWidget:
        """Construit la page de demo interactive."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 10, 40, 30)
        layout.setSpacing(12)

        title = QLabel("Essayez maintenant !")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel("Cliquez sur Dicter, parlez, et voyez le resultat")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Zone de texte resultat
        self._demo_text = QTextEdit()
        self._demo_text.setReadOnly(True)
        self._demo_text.setPlaceholderText("Votre texte apparaitra ici...")
        self._demo_text.setMinimumHeight(100)
        self._demo_text.setMaximumHeight(140)
        layout.addWidget(self._demo_text)

        # Bouton Dicter
        self._demo_btn = QPushButton("Dicter")
        self._demo_btn.setObjectName("dictate-btn")
        self._demo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._demo_btn.clicked.connect(self._toggle_demo_recording)
        layout.addWidget(self._demo_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status label
        self._demo_status = QLabel("")
        self._demo_status.setObjectName("hint")
        self._demo_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._demo_status)

        layout.addStretch()

        # Navigation
        nav = QHBoxLayout()
        btn_prev = QPushButton("Precedent")
        btn_prev.setObjectName("secondary")
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.clicked.connect(lambda: self._go_to(3))
        nav.addWidget(btn_prev)

        nav.addStretch()

        # Bouton Passer (apparait apres 10s)
        self._demo_skip_btn = QPushButton("Passer")
        self._demo_skip_btn.setObjectName("skip-btn")
        self._demo_skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._demo_skip_btn.setVisible(False)
        self._demo_skip_btn.clicked.connect(lambda: self._go_to(5))
        nav.addWidget(self._demo_skip_btn)

        self._demo_next_btn = QPushButton("Suivant")
        self._demo_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._demo_next_btn.setEnabled(False)
        self._demo_next_btn.clicked.connect(lambda: self._go_to(5))
        nav.addWidget(self._demo_next_btn)

        layout.addLayout(nav)

        return page

    def _on_demo_page_entered(self) -> None:
        """Demarre le timer pour le bouton Passer quand on arrive sur la page demo."""
        if not self._demo_success:
            QTimer.singleShot(10000, self._show_demo_skip)

    def _show_demo_skip(self) -> None:
        """Affiche le bouton Passer apres 10s."""
        if self._stack.currentIndex() == 4 and not self._demo_success:
            self._demo_skip_btn.setVisible(True)

    def _toggle_demo_recording(self) -> None:
        """Toggle enregistrement de la demo."""
        if self._demo_recording:
            self._stop_demo_recording()
        else:
            self._start_demo_recording()

    def _start_demo_recording(self) -> None:
        """Demarre l'enregistrement demo."""
        self._demo_audio_chunks = []
        self._demo_recording = True
        self._demo_btn.setText("Arreter")
        self._demo_btn.setStyleSheet("background-color: #ef4444;")
        self._demo_status.setText("Parlez maintenant...")
        self._demo_text.setPlainText("")

        try:
            self._demo_stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="float32",
                blocksize=1024,
                callback=self._demo_audio_callback,
            )
            self._demo_stream.start()
        except Exception as e:
            logger.error(f"Erreur ouverture micro demo: {e}")
            self._demo_status.setText("Erreur micro !")
            self._demo_recording = False
            self._demo_btn.setText("Dicter")
            self._demo_btn.setStyleSheet("")

    def _demo_audio_callback(self, indata: np.ndarray, frames: int, time_info: object, status: object) -> None:
        """Callback audio pour la demo."""
        self._demo_audio_chunks.append(indata.copy())

    def _stop_demo_recording(self) -> None:
        """Arrete l'enregistrement et lance la transcription."""
        self._demo_recording = False
        self._demo_btn.setText("Dicter")
        self._demo_btn.setStyleSheet("")

        if self._demo_stream:
            try:
                self._demo_stream.stop()
                self._demo_stream.close()
            except Exception:
                pass
            self._demo_stream = None

        if not self._demo_audio_chunks:
            self._demo_status.setText("Aucun audio capture")
            return

        # Concatener l'audio
        audio = np.concatenate(self._demo_audio_chunks, axis=0).flatten()

        if self._engine and self._processor:
            self._demo_btn.setEnabled(False)
            self._demo_status.setText("Transcription en cours...")

            # Lancer dans un thread
            self._demo_worker = _TranscriptionWorker(audio, self._engine, self._processor)
            self._demo_worker.finished.connect(self._on_demo_transcription_done)
            self._demo_worker.error.connect(self._on_demo_transcription_error)
            self._demo_worker_thread = threading.Thread(target=self._demo_worker.run, daemon=True)
            self._demo_worker_thread.start()
        else:
            self._demo_status.setText("Moteur non disponible — passez a l'etape suivante")
            self._demo_skip_btn.setVisible(True)

    @Slot(str)
    def _on_demo_transcription_done(self, text: str) -> None:
        """Callback quand la transcription demo est terminee."""
        self._demo_btn.setEnabled(True)
        if text:
            self._demo_text.setPlainText(text)
            self._demo_status.setText("Bravo ! Votre premiere dictee !")
            self._demo_success = True
            self._demo_next_btn.setEnabled(True)
        else:
            self._demo_status.setText("Texte vide — reessayez en parlant plus fort")

    @Slot(str)
    def _on_demo_transcription_error(self, error: str) -> None:
        """Callback en cas d'erreur de transcription demo."""
        self._demo_btn.setEnabled(True)
        self._demo_status.setText(f"Erreur — reessayez ou passez")
        self._demo_skip_btn.setVisible(True)
        logger.error(f"Demo transcription error: {error}")

    # ================================================================
    # Page 5 : Ton d'ecriture
    # ================================================================

    def _build_page_tone(self) -> QWidget:
        """Construit la page de choix du ton d'ecriture."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 10, 40, 30)
        layout.setSpacing(12)

        title = QLabel("Comment voulez-vous ecrire ?")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel("Choisissez le style de nettoyage de vos dictees")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Carte Naturel
        naturel_card = _ClickableCard(
            "Naturel",
            "Garde votre style oral, corrections minimales",
        )
        naturel_card.clicked.connect(lambda: self._select_tone("verbatim"))
        layout.addWidget(naturel_card)

        # Exemple avant/apres pour Naturel
        ex_naturel = QLabel(
            '  Avant : "euh je pense que du coup on devrait se voir demain"\n'
            '  Apres : "je pense qu\'on devrait se voir demain"'
        )
        ex_naturel.setObjectName("hint")
        ex_naturel.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 11px; margin-left: 16px;")
        layout.addWidget(ex_naturel)

        layout.addSpacing(6)

        # Carte Professionnel
        pro_card = _ClickableCard(
            "Professionnel",
            "Reformule proprement, ton formel",
        )
        pro_card.clicked.connect(lambda: self._select_tone("quality"))
        layout.addWidget(pro_card)

        # Exemple avant/apres pour Pro
        ex_pro = QLabel(
            '  Avant : "euh je pense que du coup on devrait se voir demain"\n'
            '  Apres : "Je pense que nous devrions nous voir demain."'
        )
        ex_pro.setObjectName("hint")
        ex_pro.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 11px; margin-left: 16px;")
        layout.addWidget(ex_pro)

        self._tone_cards = {"verbatim": naturel_card, "quality": pro_card}

        # Pre-selectionner Naturel
        naturel_card.selected = True

        layout.addStretch()

        # Navigation
        nav = QHBoxLayout()
        btn_prev = QPushButton("Precedent")
        btn_prev.setObjectName("secondary")
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.clicked.connect(lambda: self._go_to(4))
        nav.addWidget(btn_prev)
        nav.addStretch()

        btn_next = QPushButton("Suivant")
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.clicked.connect(lambda: self._go_to(6))
        nav.addWidget(btn_next)

        layout.addLayout(nav)
        return page

    def _select_tone(self, mode: str) -> None:
        """Selectionne un mode de nettoyage (radio behavior)."""
        self._cleaning_mode = mode
        for key, card in self._tone_cards.items():
            card.selected = (key == mode)

    # ================================================================
    # Page 6 : Pret !
    # ================================================================

    def _build_page_ready(self) -> QWidget:
        """Construit la page finale."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 30)
        layout.setSpacing(16)

        layout.addStretch()

        # Titre
        title = QLabel("Tout est pret !")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Message encourageant
        encourage = QLabel("Vous etes pret a dicter 4x plus vite")
        encourage.setObjectName("subtitle")
        encourage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(encourage)

        layout.addSpacing(10)

        # Rappel hotkey en grand
        self._hotkey_reminder = QLabel()
        self._hotkey_reminder.setObjectName("hotkey-reminder")
        self._hotkey_reminder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hotkey_reminder)

        # Rappel du mode
        self._mode_reminder = QLabel()
        self._mode_reminder.setObjectName("mode-reminder")
        self._mode_reminder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._mode_reminder)

        layout.addSpacing(10)

        # Indication tray
        hint = QLabel("Vous pouvez modifier les parametres a tout moment\nvia l'icone dans la barre de taches (clic droit).")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()

        # Bouton Terminer
        btn = QPushButton("Terminer")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    # ================================================================
    # Properties
    # ================================================================

    @property
    def hotkey(self) -> str:
        """Retourne le hotkey choisi par l'utilisateur."""
        return self._hotkey

    @property
    def cleaning_mode(self) -> str:
        """Retourne le mode de nettoyage choisi."""
        return self._cleaning_mode

    def closeEvent(self, event: object) -> None:
        """Nettoie les streams audio si le dialog est ferme."""
        self._stop_mic_test()
        # Nettoyer la demo aussi
        if self._demo_stream:
            try:
                self._demo_stream.stop()
                self._demo_stream.close()
            except Exception:
                pass
            self._demo_stream = None
        super().closeEvent(event)
