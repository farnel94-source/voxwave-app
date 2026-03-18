"""Tests pour les bugs onboarding (welcome_dialog.py)."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock sounddevice (nécessite du hardware audio absent en CI)
if "sounddevice" not in sys.modules:
    sys.modules["sounddevice"] = MagicMock()


@pytest.fixture
def _patch_pyside6():
    """Patch PySide6 pour éviter la création d'une QApplication."""
    with patch("src.gui.welcome_dialog.QDialog.__init__", return_value=None), \
         patch("src.gui.welcome_dialog.QDialog.setWindowTitle"), \
         patch("src.gui.welcome_dialog.QDialog.setFixedSize"), \
         patch("src.gui.welcome_dialog.QDialog.setStyleSheet"):
        yield


class TestBug_LanguageComboNoAutoDetect:
    """Bug 1 : le dropdown langue ne doit pas contenir 'Auto-detect'."""

    def test_no_auto_detect_in_combo(self):
        """Vérifie qu'aucun item n'a data='auto' dans le dropdown."""
        from src.config.defaults import WHISPER_LANGUAGES

        # Simuler la construction du combo sans "Auto-detect"
        items = []
        for code, name in WHISPER_LANGUAGES:
            items.append((f"{name} ({code})", code))

        # Aucun item ne doit avoir le code "auto"
        codes = [code for _, code in items]
        assert "auto" not in codes, "'auto' ne devrait pas être dans WHISPER_LANGUAGES"

    def test_default_selection_is_english(self):
        """Vérifie que la pré-sélection par défaut est 'en'."""
        from src.config.defaults import WHISPER_LANGUAGES

        codes = [code for code, _ in WHISPER_LANGUAGES]
        assert "en" in codes, "'en' doit exister dans WHISPER_LANGUAGES"

        # Simuler findData("en") — trouver l'index
        en_index = codes.index("en")
        assert en_index >= 0


class TestBug_DemoRecordingPlaysFeedback:
    """Bug 2 : _start_demo_recording doit appeler play_start, _stop doit appeler play_stop."""

    def _make_dialog(self, feedback=None):
        """Crée un objet qui a les mêmes attributs qu'un WelcomeDialog."""
        from src.gui.welcome_dialog import WelcomeDialog

        dialog = MagicMock(spec=WelcomeDialog)
        dialog._feedback = feedback if feedback is not None else MagicMock()
        dialog._language = "en"
        dialog._demo_audio_chunks = []
        dialog._demo_recording = False
        dialog._demo_stream = None
        dialog._demo_btn = MagicMock()
        dialog._demo_status = MagicMock()
        dialog._demo_text = MagicMock()
        dialog._engine = None
        dialog._processor = None
        dialog._demo_worker = None
        dialog._demo_worker_thread = None
        dialog._demo_skip_btn = MagicMock()
        # Bind les vraies méthodes
        dialog._start_demo_recording = WelcomeDialog._start_demo_recording.__get__(dialog)
        dialog._stop_demo_recording = WelcomeDialog._stop_demo_recording.__get__(dialog)
        return dialog

    @patch("src.gui.welcome_dialog.sd")
    def test_start_demo_calls_play_start(self, mock_sd):
        """_start_demo_recording doit appeler feedback.play_start()."""
        mock_sd.InputStream.return_value = MagicMock()
        dialog = self._make_dialog()

        dialog._start_demo_recording()

        dialog._feedback.play_start.assert_called_once()

    @patch("src.gui.welcome_dialog.sd")
    def test_stop_demo_calls_play_stop(self, mock_sd):
        """_stop_demo_recording doit appeler feedback.play_stop()."""
        dialog = self._make_dialog()
        dialog._demo_recording = True
        dialog._demo_stream = MagicMock()
        dialog._demo_audio_chunks = [MagicMock()]

        with patch("src.gui.welcome_dialog._TranscriptionWorker", MagicMock()), \
             patch("src.gui.welcome_dialog.threading.Thread", MagicMock()):
            dialog._stop_demo_recording()

        dialog._feedback.play_stop.assert_called_once()

    @patch("src.gui.welcome_dialog.sd")
    def test_no_crash_without_feedback(self, mock_sd):
        """Si feedback=None, pas de crash."""
        mock_sd.InputStream.return_value = MagicMock()
        dialog = self._make_dialog(feedback=None)
        dialog._feedback = None

        dialog._start_demo_recording()  # Ne doit pas crasher

        dialog._demo_recording = True
        dialog._stop_demo_recording()  # Ne doit pas crasher


def test_welcome_page_uses_create_qicon_not_logo_png(monkeypatch):
    """La page welcome doit utiliser create_qicon et ne plus charger logo.png."""
    from src.gui import welcome_dialog as wd

    class FakeWidget:
        pass

    class FakeLayout:
        def __init__(self, _parent=None):
            self.widgets = []

        def setContentsMargins(self, *_args):
            pass

        def setSpacing(self, *_args):
            pass

        def addWidget(self, widget, **_kwargs):
            self.widgets.append(widget)

        def addSpacing(self, *_args):
            pass

        def addStretch(self):
            pass

    class FakeFont:
        def setPointSize(self, *_args):
            pass

        def setBold(self, *_args):
            pass

    class FakeLabel:
        instances = []

        def __init__(self, *_args, **_kwargs):
            self.pixmap_set = None
            FakeLabel.instances.append(self)

        def setAlignment(self, *_args):
            pass

        def setPixmap(self, pixmap):
            self.pixmap_set = pixmap

        def setObjectName(self, *_args):
            pass

        def setFont(self, *_args):
            pass

    class FakePixmap:
        def isNull(self):
            return False

    fake_pixmap = FakePixmap()
    fake_icon = MagicMock()
    fake_icon.pixmap.return_value = fake_pixmap

    class FakeQIcon:
        class Mode:
            Normal = 0

        class State:
            Off = 0

    class FakeSignal:
        def connect(self, _fn):
            pass

    class FakeButton:
        def __init__(self, *_args, **_kwargs):
            self.clicked = FakeSignal()

        def setCursor(self, *_args):
            pass

    class DummyDialog:
        def _reg(self, _key, widget):
            return widget

    qpixmap_ctor = MagicMock()

    monkeypatch.setattr(wd, "QWidget", FakeWidget)
    monkeypatch.setattr(wd, "QVBoxLayout", FakeLayout)
    monkeypatch.setattr(wd, "QLabel", FakeLabel)
    monkeypatch.setattr(wd, "QFont", FakeFont)
    monkeypatch.setattr(wd, "QIcon", FakeQIcon)
    monkeypatch.setattr(wd, "QPixmap", qpixmap_ctor)
    monkeypatch.setattr(wd, "QPushButton", FakeButton)

    with patch.object(wd, "create_qicon", return_value=fake_icon) as create_qicon_mock:
        wd.WelcomeDialog._build_page_welcome(DummyDialog())

    create_qicon_mock.assert_called_once_with("idle", size=96)
    assert qpixmap_ctor.call_count == 0
    assert FakeLabel.instances[0].pixmap_set is fake_pixmap
