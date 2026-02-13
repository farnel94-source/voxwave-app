"""Tests pour src/hotkey/listener.py."""

import time
from unittest.mock import patch, MagicMock

import pytest

from src.hotkey.listener import HotkeyListener


class TestHotkeyListener:
    """Tests HotkeyListener."""

    @patch.object(HotkeyListener, "_detect_backend", return_value="pynput")
    def test_init_defaults(self, mock_backend):
        listener = HotkeyListener()
        assert listener.hotkey == "F8"
        assert listener.is_recording is False

    @patch.object(HotkeyListener, "_detect_backend", return_value="pynput")
    def test_init_custom_hotkey(self, mock_backend):
        listener = HotkeyListener(hotkey="F9")
        assert listener.hotkey == "F9"

    @patch.object(HotkeyListener, "_detect_backend", return_value="pynput")
    def test_set_processing(self, mock_backend):
        listener = HotkeyListener()
        listener.set_processing(True)
        assert listener._is_processing is True
        listener.set_processing(False)
        assert listener._is_processing is False

    @patch.object(HotkeyListener, "_detect_backend", return_value="pynput")
    def test_handle_hotkey_triggers_start(self, mock_backend):
        on_start = MagicMock()
        on_stop = MagicMock()
        listener = HotkeyListener(on_start=on_start, on_stop=on_stop)
        listener._last_press_time = 0
        listener._handle_hotkey()
        on_start.assert_called_once()
        assert listener.is_recording is True

    @patch.object(HotkeyListener, "_detect_backend", return_value="pynput")
    def test_handle_hotkey_triggers_stop(self, mock_backend):
        on_start = MagicMock()
        on_stop = MagicMock()
        listener = HotkeyListener(on_start=on_start, on_stop=on_stop)
        listener._last_press_time = 0
        listener._handle_hotkey()  # Start
        listener._last_press_time = 0  # Reset debounce
        listener._handle_hotkey()  # Stop
        on_stop.assert_called_once()

    @patch.object(HotkeyListener, "_detect_backend", return_value="pynput")
    def test_on_press_pynput_triggers_start(self, mock_backend):
        on_start = MagicMock()
        listener = HotkeyListener(on_start=on_start)
        from pynput.keyboard import Key
        listener._last_press_time = 0
        listener._on_press_pynput(Key.f8)
        on_start.assert_called_once()

    @patch.object(HotkeyListener, "_detect_backend", return_value="pynput")
    def test_debounce_ignores_rapid_presses(self, mock_backend):
        on_start = MagicMock()
        listener = HotkeyListener(on_start=on_start)
        from pynput.keyboard import Key
        listener._on_press_pynput(Key.f8)
        listener._on_press_pynput(Key.f8)  # Should be debounced
        on_start.assert_called_once()

    @patch.object(HotkeyListener, "_detect_backend", return_value="pynput")
    def test_ignores_when_processing(self, mock_backend):
        on_start = MagicMock()
        listener = HotkeyListener(on_start=on_start)
        listener.set_processing(True)
        from pynput.keyboard import Key
        listener._last_press_time = 0
        listener._on_press_pynput(Key.f8)
        on_start.assert_not_called()

    @patch.object(HotkeyListener, "_detect_backend", return_value="pynput")
    def test_ignores_other_keys(self, mock_backend):
        on_start = MagicMock()
        listener = HotkeyListener(on_start=on_start)
        from pynput.keyboard import Key
        listener._on_press_pynput(Key.f9)
        on_start.assert_not_called()

    @patch.object(HotkeyListener, "_detect_backend", return_value="pynput")
    @patch("pynput.keyboard.Listener")
    def test_start_creates_listener(self, mock_listener_class, mock_backend):
        listener = HotkeyListener()
        listener.start()
        mock_listener_class.assert_called_once()

    @patch.object(HotkeyListener, "_detect_backend", return_value="pynput")
    @patch("pynput.keyboard.Listener")
    def test_stop(self, mock_listener_class, mock_backend):
        listener = HotkeyListener()
        mock_instance = MagicMock()
        mock_listener_class.return_value = mock_instance
        listener.start()
        listener.stop()
        mock_instance.stop.assert_called_once()


class TestHotkeyListenerBackendDetection:
    """Tests de la detection du backend."""

    @patch("sys.platform", "win32")
    def test_windows_uses_pynput(self):
        assert HotkeyListener._detect_backend() == "pynput"

    @patch("sys.platform", "darwin")
    def test_darwin_uses_pynput(self):
        assert HotkeyListener._detect_backend() == "pynput"
