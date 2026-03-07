"""Tests pour le focus des dialogs Settings/Help."""

import sys
import types
from unittest.mock import MagicMock, patch

from src.app import TheWave
import src.app as app_module
from PySide6.QtCore import Qt
from src.gui.settings_dialog import SettingsDialog


def _build_fake_settings_module(sample_config, captured_kwargs, instances):
    """Construit un faux module SettingsDialog pour tester _on_settings/_on_help."""
    fake_module = types.ModuleType("src.gui.settings_dialog")

    class FakeSettingsDialog:
        def __init__(self, **kwargs):
            captured_kwargs.append(kwargs)
            instances.append(self)
            self.hotkey = sample_config["hotkey"]
            self.cleaning_mode = sample_config["cleaning"]["mode"]
            self.system_language = sample_config["language"]
            self.language = sample_config["whisper"]["language"]
            self.device_id = sample_config["audio"]["device_id"]
            self.transcription_provider = sample_config["transcription"]["provider"]
            self.cleaning_provider = sample_config["cleaning"]["provider"]
            self.ollama_host = sample_config["cleaning"].get("ollama_host", "http://localhost:11434")
            self.activation_method = sample_config.get("activation_method", "both")
            self.auto_stop_enabled = sample_config["audio"].get("auto_stop_enabled", False)
            self.auto_stop_silence_duration = sample_config["audio"].get("auto_stop_silence_duration", 2.0)
            self.navigated_to_help = False

        def exec(self):
            return 0

        def navigate_to_help(self):
            self.navigated_to_help = True

    fake_module.SettingsDialog = FakeSettingsDialog
    return fake_module


def test_focus_existing_dialog_none_is_noop(sample_config):
    """None ne doit rien faire."""
    app = TheWave(sample_config)

    with patch("src.app._force_foreground_win32") as force_fg:
        app._focus_existing_dialog(None, origin="unit-test")

    force_fg.assert_not_called()


def test_focus_existing_dialog_windows_retries(sample_config, monkeypatch):
    """Sous Windows, on schedule 2 retries (50ms, 150ms)."""
    app = TheWave(sample_config)
    dialog = MagicMock()
    dialog.isMinimized.return_value = True

    scheduled = []

    class _FakeQTimer:
        @staticmethod
        def singleShot(delay, callback):
            scheduled.append((delay, callback))

    fake_qtcore = types.ModuleType("PySide6.QtCore")
    fake_qtcore.QTimer = _FakeQTimer
    fake_pyside = types.ModuleType("PySide6")
    fake_pyside.QtCore = fake_qtcore

    monkeypatch.setitem(sys.modules, "PySide6", fake_pyside)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", fake_qtcore)

    with patch.object(app_module.sys, "platform", "win32"):
        with patch("src.app._force_foreground_win32") as force_fg:
            app._focus_existing_dialog(dialog, origin="unit-test")
            assert [delay for delay, _ in scheduled] == [50, 150]
            assert dialog.show.call_count == 1
            assert dialog.raise_.call_count == 1
            assert dialog.activateWindow.call_count == 1
            assert force_fg.call_count == 1

            for _, callback in scheduled:
                callback()

            assert dialog.show.call_count == 3
            assert dialog.raise_.call_count == 3
            assert dialog.activateWindow.call_count == 3
            assert dialog.showNormal.call_count == 3
            assert force_fg.call_count == 3


def test_on_settings_existing_dialog_uses_focus_helper(sample_config):
    """_on_settings doit focaliser le dialog existant sans en recréer un."""
    app = TheWave(sample_config)
    app._settings_dialog = MagicMock()

    with patch.object(app, "_focus_existing_dialog") as focus_helper:
        app._on_settings()

    focus_helper.assert_called_once_with(app._settings_dialog, origin="settings-existing")


def test_on_help_existing_dialog_uses_focus_helper(sample_config):
    """_on_help doit focaliser le dialog existant sans en recréer un."""
    app = TheWave(sample_config)
    app._settings_dialog = MagicMock()

    with patch.object(app, "_focus_existing_dialog") as focus_helper:
        app._on_help()

    focus_helper.assert_called_once_with(app._settings_dialog, origin="help-existing")


def test_on_settings_creates_dialog_with_parent_none(sample_config, monkeypatch):
    """Nouveau dialog settings: parent=None (pas owner minimisé taskbar)."""
    app = TheWave(sample_config)
    captured_kwargs = []
    instances = []
    fake_module = _build_fake_settings_module(sample_config, captured_kwargs, instances)
    monkeypatch.setitem(sys.modules, "src.gui.settings_dialog", fake_module)

    with patch.object(app, "_focus_existing_dialog") as focus_helper:
        app._on_settings()

    assert len(captured_kwargs) == 1
    assert captured_kwargs[0]["parent"] is None
    assert len(instances) == 1
    focus_helper.assert_called_once_with(instances[0], origin="settings-new")


def test_on_help_creates_dialog_with_parent_none(sample_config, monkeypatch):
    """Nouveau dialog help: parent=None (pas owner minimisé taskbar)."""
    app = TheWave(sample_config)
    captured_kwargs = []
    instances = []
    fake_module = _build_fake_settings_module(sample_config, captured_kwargs, instances)
    monkeypatch.setitem(sys.modules, "src.gui.settings_dialog", fake_module)

    with patch.object(app, "_focus_existing_dialog") as focus_helper:
        app._on_help()

    assert len(captured_kwargs) == 1
    assert captured_kwargs[0]["parent"] is None
    assert len(instances) == 1
    assert instances[0].navigated_to_help is True
    focus_helper.assert_called_once_with(instances[0], origin="help-new")


def test_force_foreground_win32_uses_restore_bring_setfg(monkeypatch):
    """_force_foreground_win32 doit appeler ShowWindow/BringWindowToTop/SetForegroundWindow."""
    calls = []

    class FakeUser32:
        def GetForegroundWindow(self):
            calls.append(("GetForegroundWindow",))
            return 111

        def GetWindowThreadProcessId(self, hwnd, _pid):
            calls.append(("GetWindowThreadProcessId", hwnd))
            return 10 if hwnd == 111 else 20

        def AttachThreadInput(self, src_tid, dst_tid, attach):
            calls.append(("AttachThreadInput", src_tid, dst_tid, attach))
            return 1

        def ShowWindow(self, hwnd, cmd):
            calls.append(("ShowWindow", hwnd, cmd))
            return 1

        def BringWindowToTop(self, hwnd):
            calls.append(("BringWindowToTop", hwnd))
            return 1

        def SetForegroundWindow(self, hwnd):
            calls.append(("SetForegroundWindow", hwnd))
            return 1

        def SetWindowPos(self, hwnd, h_after, x, y, cx, cy, flags):
            calls.append(("SetWindowPos", hwnd, h_after, flags))
            return 1

    fake_ctypes = types.ModuleType("ctypes")
    fake_ctypes.windll = types.SimpleNamespace(user32=FakeUser32())
    monkeypatch.setitem(sys.modules, "ctypes", fake_ctypes)

    widget = MagicMock()
    widget.winId.return_value = 999

    with patch.object(app_module.sys, "platform", "win32"):
        app_module._force_foreground_win32(widget)

    assert ("ShowWindow", 999, 9) in calls
    assert ("BringWindowToTop", 999) in calls
    assert ("SetForegroundWindow", 999) in calls
    assert ("SetWindowPos", 999, -1, 0x0002 | 0x0001 | 0x0040) in calls
    assert ("SetWindowPos", 999, -2, 0x0002 | 0x0001 | 0x0040) in calls
    assert ("AttachThreadInput", 10, 20, True) in calls
    assert ("AttachThreadInput", 10, 20, False) in calls


def test_settings_dialog_setup_window_sets_tool_flag_on_windows():
    """Sous Windows, _setup_window ajoute Qt.Tool."""

    class DummyDialog:
        def __init__(self):
            self._sys_lang = "en"
            self._flags = Qt.WindowType.Widget

        def setWindowTitle(self, _value):
            pass

        def setFixedSize(self, _w, _h):
            pass

        def setStyleSheet(self, _style):
            pass

        def setWindowFlags(self, flags):
            self._flags = flags

        def windowFlags(self):
            return self._flags

    dummy = DummyDialog()
    with patch("src.gui.settings_dialog.sys.platform", "win32"):
        SettingsDialog._setup_window(dummy)

    base_type = dummy.windowFlags() & Qt.WindowType.WindowType_Mask
    assert base_type == Qt.WindowType.Tool


def test_settings_dialog_setup_window_no_tool_flag_on_linux():
    """Sous Linux, _setup_window ne met pas Qt.Tool."""

    class DummyDialog:
        def __init__(self):
            self._sys_lang = "en"
            self._flags = Qt.WindowType.Widget

        def setWindowTitle(self, _value):
            pass

        def setFixedSize(self, _w, _h):
            pass

        def setStyleSheet(self, _style):
            pass

        def setWindowFlags(self, flags):
            self._flags = flags

        def windowFlags(self):
            return self._flags

    dummy = DummyDialog()
    with patch("src.gui.settings_dialog.sys.platform", "linux"):
        SettingsDialog._setup_window(dummy)

    base_type = dummy.windowFlags() & Qt.WindowType.WindowType_Mask
    assert base_type != Qt.WindowType.Tool
