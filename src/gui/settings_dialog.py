"""Dialogue de parametres VoxTool — UI moderne inspiree Wispr/Aqua."""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
    QPushButton,
)

logger = logging.getLogger(__name__)

# Mapping Qt modifier flags -> noms
_QT_MODIFIER_NAMES = {
    Qt.KeyboardModifier.ControlModifier: "Ctrl",
    Qt.KeyboardModifier.ShiftModifier: "Shift",
    Qt.KeyboardModifier.AltModifier: "Alt",
    Qt.KeyboardModifier.MetaModifier: "Cmd",
}

# Mapping Qt key codes -> noms lisibles
_QT_KEY_NAMES: dict = {}
for _i in range(1, 13):
    _QT_KEY_NAMES[getattr(Qt.Key, f"Key_F{_i}")] = f"F{_i}"
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    _QT_KEY_NAMES[getattr(Qt.Key, f"Key_{_c}")] = _c
for _d in "0123456789":
    _QT_KEY_NAMES[getattr(Qt.Key, f"Key_{_d}")] = _d
_QT_KEY_NAMES.update({
    Qt.Key.Key_Space: "Space",
    Qt.Key.Key_Return: "Enter",
    Qt.Key.Key_Tab: "Tab",
    Qt.Key.Key_Escape: "Esc",
    Qt.Key.Key_Backspace: "Backspace",
    Qt.Key.Key_Delete: "Delete",
    Qt.Key.Key_Home: "Home",
    Qt.Key.Key_End: "End",
    Qt.Key.Key_PageUp: "PageUp",
    Qt.Key.Key_PageDown: "PageDown",
    Qt.Key.Key_Up: "Up",
    Qt.Key.Key_Down: "Down",
    Qt.Key.Key_Left: "Left",
    Qt.Key.Key_Right: "Right",
    Qt.Key.Key_Insert: "Insert",
})

# ====================================================================
# Styles
# ====================================================================

_STYLESHEET = """
QDialog {
    background-color: #18181b;
    color: #ffffff;
}
QLabel {
    color: #ffffff;
    background: transparent;
}
QLabel#section-title {
    color: rgba(255, 255, 255, 0.4);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
}
QLabel#hint {
    color: rgba(255, 255, 255, 0.4);
    font-size: 11px;
}
QLabel#nav-item {
    color: rgba(255, 255, 255, 0.6);
    font-size: 13px;
    padding: 8px 16px;
    border-radius: 8px;
}
QLabel#nav-item-active {
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 8px;
    background-color: rgba(255, 255, 255, 0.08);
}
QLineEdit {
    background-color: rgba(255, 255, 255, 0.08);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    font-weight: bold;
}
QLineEdit:focus {
    border-color: #3b82f6;
}
QComboBox {
    background-color: rgba(255, 255, 255, 0.08);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    min-width: 180px;
}
QComboBox:hover {
    border-color: rgba(255, 255, 255, 0.3);
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid rgba(255, 255, 255, 0.5);
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #27272a;
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    selection-background-color: rgba(59, 130, 246, 0.3);
    padding: 4px;
}
QPushButton#close-btn {
    background-color: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
}
QPushButton#close-btn:hover {
    background-color: rgba(255, 255, 255, 0.12);
    color: #ffffff;
}
"""


# ====================================================================
# HotkeyCapture (reutilise dans welcome_dialog aussi)
# ====================================================================

class HotkeyCapture(QLineEdit):
    """Champ de saisie qui capture les combos de touches."""

    def __init__(self, current_hotkey: str = "F8", parent: Optional[object] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Appuyez sur une combinaison de touches...")
        self.setText(current_hotkey)
        self._captured_hotkey = current_hotkey

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Capture les combos de touches."""
        key = event.key()

        # Ignorer les appuis de modifier seuls
        if key in (
            Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt,
            Qt.Key.Key_Meta, Qt.Key.Key_AltGr,
        ):
            return

        key_name = _QT_KEY_NAMES.get(key)
        if key_name is None:
            return

        # Construire la chaine combo
        parts = []
        modifiers = event.modifiers()
        for mod_flag, mod_name in _QT_MODIFIER_NAMES.items():
            if modifiers & mod_flag:
                parts.append(mod_name)
        parts.append(key_name)

        combo = "+".join(parts)
        self._captured_hotkey = combo
        self.setText(combo)

    @property
    def captured_hotkey(self) -> str:
        """Retourne le hotkey capture."""
        return self._captured_hotkey


# ====================================================================
# NavItem (bouton de navigation gauche)
# ====================================================================

class _NavItem(QLabel):
    """Item de navigation cliquable dans la sidebar."""

    clicked = Signal()

    def __init__(self, text: str, icon: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._text = text
        self._icon = icon
        self._active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText(f"{icon}  {text}" if icon else text)
        self.setObjectName("nav-item")

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = value
        self.setObjectName("nav-item-active" if value else "nav-item")
        self.setStyleSheet(self.styleSheet())  # force refresh

    def mousePressEvent(self, event: object) -> None:
        self.clicked.emit()


# ====================================================================
# ToneCard (carte cliquable pour le mode d'ecriture)
# ====================================================================

class _ToneCard(QWidget):
    """Carte de selection du ton d'ecriture."""

    clicked = Signal()

    _BG_NORMAL = QColor(255, 255, 255, 13)
    _BG_HOVER = QColor(255, 255, 255, 25)
    _BG_SELECTED = QColor(59, 130, 246, 38)
    _BORDER_NORMAL = QColor(255, 255, 255, 25)
    _BORDER_HOVER = QColor(255, 255, 255, 60)
    _BORDER_SELECTED = QColor(59, 130, 246, 255)

    def __init__(self, title: str, description: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._selected = False
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        self._check = QLabel("")
        self._check.setFixedWidth(18)
        self._check.setStyleSheet("font-size: 14px; color: #3b82f6; background: transparent; border: none;")
        self._check.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._check)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        title_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text_layout.addWidget(title_lbl)
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 11px; background: transparent; border: none;")
        desc_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text_layout.addWidget(desc_lbl)
        layout.addLayout(text_layout)

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool) -> None:
        self._selected = value
        self._check.setText("\u2713" if value else "")
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
            bg, border = self._BG_SELECTED, self._BORDER_SELECTED
        elif self._hovered:
            bg, border = self._BG_HOVER, self._BORDER_HOVER
        else:
            bg, border = self._BG_NORMAL, self._BORDER_NORMAL
        painter.setBrush(bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 10, 10)
        painter.setPen(QPen(border, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 10, 10)
        painter.end()


# ====================================================================
# SettingsDialog principal
# ====================================================================

class SettingsDialog(QDialog):
    """Dialogue de parametres VoxTool — design moderne avec navigation laterale."""

    def __init__(
        self,
        current_hotkey: str = "F8",
        current_cleaning_mode: str = "verbatim",
        current_language: str = "fr",
        current_device_id: Optional[int] = None,
        current_transcription_provider: str = "hybrid",
        current_cleaning_provider: str = "hybrid",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._hotkey = current_hotkey
        self._cleaning_mode = current_cleaning_mode
        self._language = current_language
        self._device_id = current_device_id
        self._transcription_provider = current_transcription_provider
        self._cleaning_provider = current_cleaning_provider

        self._setup_window()
        self._build_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle("VoxTool — Parametres")
        self.setFixedSize(580, 420)
        self.setStyleSheet(_STYLESHEET)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Sidebar gauche ----
        sidebar = QWidget()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet("background-color: rgba(255,255,255,0.03);")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(4)

        # Titre sidebar
        title = QLabel("Parametres")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff; padding: 0 16px 12px 16px;")
        sidebar_layout.addWidget(title)

        # Nav items
        self._nav_items: list[_NavItem] = []
        nav_labels = [
            ("General", "\u2699"),
            ("Ecriture", "\u270e"),
            ("Audio", "\u266b"),
            ("Avance", "\u2699"),
        ]
        for i, (label, icon) in enumerate(nav_labels):
            nav = _NavItem(label, icon)
            nav.clicked.connect(lambda idx=i: self._navigate(idx))
            self._nav_items.append(nav)
            sidebar_layout.addWidget(nav)

        sidebar_layout.addStretch()

        # Version
        version = QLabel("VoxTool v2.0")
        version.setStyleSheet("color: rgba(255,255,255,0.25); font-size: 10px; padding: 0 16px;")
        sidebar_layout.addWidget(version)

        root.addWidget(sidebar)

        # ---- Contenu droite ----
        self._content_stack = QVBoxLayout()
        self._content_stack.setContentsMargins(24, 20, 24, 20)

        # Pages
        self._pages: list[QWidget] = []
        self._pages.append(self._build_page_general())
        self._pages.append(self._build_page_writing())
        self._pages.append(self._build_page_audio())
        self._pages.append(self._build_page_advanced())

        # On utilise un stacked widget simple
        from PySide6.QtWidgets import QStackedWidget
        self._stack = QStackedWidget()
        for page in self._pages:
            self._stack.addWidget(page)
        self._content_stack.addWidget(self._stack)

        # Bouton Fermer en bas
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("close-btn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        self._content_stack.addLayout(close_row)

        content_widget = QWidget()
        content_widget.setLayout(self._content_stack)
        root.addWidget(content_widget)

        # Activer le premier onglet
        self._navigate(0)

    def _navigate(self, index: int) -> None:
        """Change l'onglet actif."""
        for i, nav in enumerate(self._nav_items):
            nav.active = (i == index)
        self._stack.setCurrentIndex(index)

    # ================================================================
    # Page General
    # ================================================================

    def _build_page_general(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Section title
        layout.addWidget(self._section_title("GENERAL"))

        # Raccourci clavier
        layout.addWidget(self._field_label("Raccourci clavier"))
        self._hotkey_capture = HotkeyCapture(self._hotkey)
        self._hotkey_capture.setMinimumHeight(40)
        layout.addWidget(self._hotkey_capture)
        hint = QLabel("Cliquez puis appuyez sur la combinaison souhaitee (ex: F8, Ctrl+Shift+V)")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addSpacing(8)

        # Langue
        layout.addWidget(self._field_label("Langue de dictee"))
        self._lang_combo = QComboBox()
        languages = [
            ("fr", "Francais"),
            ("en", "English"),
            ("es", "Espanol"),
            ("de", "Deutsch"),
            ("it", "Italiano"),
            ("pt", "Portugues"),
            ("nl", "Nederlands"),
            ("ja", "Japanese"),
            ("ko", "Korean"),
            ("zh", "Chinese"),
            ("ru", "Russian"),
            ("ar", "Arabic"),
            ("tr", "Turkish"),
            ("pl", "Polish"),
            ("sv", "Swedish"),
        ]
        current_lang_idx = 0
        for i, (code, name) in enumerate(languages):
            self._lang_combo.addItem(f"{name} ({code})", code)
            if code == self._language:
                current_lang_idx = i
        self._lang_combo.setCurrentIndex(current_lang_idx)
        layout.addWidget(self._lang_combo)

        layout.addStretch()
        return page

    # ================================================================
    # Page Ecriture
    # ================================================================

    def _build_page_writing(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._section_title("MODE D'ECRITURE"))

        desc = QLabel("Comment VoxTool doit nettoyer vos dictees ?")
        desc.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(4)

        # Carte Naturel
        self._tone_natural = _ToneCard("Naturel", "Garde votre style oral, corrections minimales")
        self._tone_natural.clicked.connect(lambda: self._select_mode("verbatim"))
        layout.addWidget(self._tone_natural)

        ex1 = QLabel('  "je pense qu\'on devrait se voir demain"')
        ex1.setObjectName("hint")
        layout.addWidget(ex1)

        layout.addSpacing(4)

        # Carte Pro
        self._tone_pro = _ToneCard("Professionnel", "Reformule proprement, ton formel")
        self._tone_pro.clicked.connect(lambda: self._select_mode("quality"))
        layout.addWidget(self._tone_pro)

        ex2 = QLabel('  "Je pense que nous devrions nous voir demain."')
        ex2.setObjectName("hint")
        layout.addWidget(ex2)

        # Pre-select
        if self._cleaning_mode == "quality":
            self._tone_pro.selected = True
        else:
            self._tone_natural.selected = True

        layout.addStretch()
        return page

    def _select_mode(self, mode: str) -> None:
        self._cleaning_mode = mode
        self._tone_natural.selected = (mode == "verbatim")
        self._tone_pro.selected = (mode == "quality")

    # ================================================================
    # Page Audio
    # ================================================================

    def _build_page_audio(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(self._section_title("PERIPHERIQUE AUDIO"))

        layout.addWidget(self._field_label("Microphone"))

        self._device_combo = QComboBox()
        self._device_combo.addItem("Defaut systeme", None)

        # Charger les devices disponibles
        try:
            from src.audio.device_manager import AudioDeviceManager
            devices = AudioDeviceManager.list_input_devices()
            current_idx = 0
            for dev in devices:
                self._device_combo.addItem(
                    f"{dev['name']} ({dev['channels']}ch)",
                    dev["id"],
                )
                if dev["id"] == self._device_id:
                    current_idx = self._device_combo.count() - 1
            self._device_combo.setCurrentIndex(current_idx)
        except Exception as e:
            logger.warning(f"Impossible de lister les peripheriques: {e}")

        layout.addWidget(self._device_combo)

        hint = QLabel("Selectionnez le micro a utiliser pour la dictee")
        hint.setObjectName("hint")
        layout.addWidget(hint)

        layout.addStretch()
        return page

    # ================================================================
    # Page Avance
    # ================================================================

    def _build_page_advanced(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(self._section_title("MOTEURS"))

        # Provider transcription
        layout.addWidget(self._field_label("Transcription"))
        self._trans_combo = QComboBox()
        trans_options = [
            ("hybrid", "Hybride (cloud + local)"),
            ("cloud", "Cloud uniquement (Groq)"),
            ("local", "Local uniquement (Whisper)"),
        ]
        current_trans_idx = 0
        for i, (val, label) in enumerate(trans_options):
            self._trans_combo.addItem(label, val)
            if val == self._transcription_provider:
                current_trans_idx = i
        self._trans_combo.setCurrentIndex(current_trans_idx)
        layout.addWidget(self._trans_combo)

        layout.addSpacing(8)

        # Provider nettoyage
        layout.addWidget(self._field_label("Nettoyage"))
        self._clean_combo = QComboBox()
        clean_options = [
            ("hybrid", "Hybride (cloud + local)"),
            ("cloud", "Cloud uniquement (OpenAI)"),
            ("local", "Local uniquement (Ollama)"),
        ]
        current_clean_idx = 0
        for i, (val, label) in enumerate(clean_options):
            self._clean_combo.addItem(label, val)
            if val == self._cleaning_provider:
                current_clean_idx = i
        self._clean_combo.setCurrentIndex(current_clean_idx)
        layout.addWidget(self._clean_combo)

        hint = QLabel("Hybride = essaie le cloud d'abord, bascule en local si indisponible")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()
        return page

    # ================================================================
    # Helpers
    # ================================================================

    def _section_title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section-title")
        return lbl

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 13px; font-weight: 600;")
        return lbl

    # ================================================================
    # Properties (lues par app.py apres dialog.exec)
    # ================================================================

    @property
    def hotkey(self) -> str:
        return self._hotkey_capture.captured_hotkey

    @property
    def cleaning_mode(self) -> str:
        return self._cleaning_mode

    @property
    def language(self) -> str:
        return self._lang_combo.currentData()

    @property
    def device_id(self) -> Optional[int]:
        return self._device_combo.currentData()

    @property
    def transcription_provider(self) -> str:
        return self._trans_combo.currentData()

    @property
    def cleaning_provider(self) -> str:
        return self._clean_combo.currentData()
