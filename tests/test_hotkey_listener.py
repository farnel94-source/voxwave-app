"""Tests pour src/hotkey/listener.py."""

import time
from unittest.mock import patch, MagicMock

import pytest

from src.hotkey.listener import HotkeyListener


class TestHotkeyListener:
    """Tests HotkeyListener."""

    def test_init_defaults(self):
        listener = HotkeyListener()
        assert listener.hotkey == "F8"
        assert listener.is_recording is False

    def test_init_custom_hotkey(self):
        listener = HotkeyListener(hotkey="F9")
        assert listener.hotkey == "F9"

    def test_set_processing(self):
        listener = HotkeyListener()
        listener.set_processing(True)
        assert listener._is_processing is True
        listener.set_processing(False)
        assert listener._is_processing is False

    def test_on_press_triggers_start(self):
        on_start = MagicMock()
        on_stop = MagicMock()
        listener = HotkeyListener(on_start=on_start, on_stop=on_stop)

        from pynput.keyboard import Key

        listener._last_press_time = 0
        # Call the real _on_press (not mocked)
        HotkeyListener._on_press(listener, Key.f8)
        on_start.assert_called_once()
        assert listener.is_recording is True

    def test_on_press_triggers_stop(self):
        on_start = MagicMock()
        on_stop = MagicMock()
        listener = HotkeyListener(on_start=on_start, on_stop=on_stop)

        from pynput.keyboard import Key

        listener._last_press_time = 0
        HotkeyListener._on_press(listener, Key.f8)  # Start
        listener._last_press_time = 0  # Reset debounce
        HotkeyListener._on_press(listener, Key.f8)  # Stop
        on_stop.assert_called_once()

    def test_debounce_ignores_rapid_presses(self):
        on_start = MagicMock()
        listener = HotkeyListener(on_start=on_start)

        from pynput.keyboard import Key

        listener._on_press(Key.f8)
        listener._on_press(Key.f8)  # Should be debounced
        # Only one call
        on_start.assert_called_once()

    def test_ignores_when_processing(self):
        on_start = MagicMock()
        listener = HotkeyListener(on_start=on_start)
        listener.set_processing(True)

        from pynput.keyboard import Key

        listener._last_press_time = 0
        listener._on_press(Key.f8)
        on_start.assert_not_called()

    def test_ignores_other_keys(self):
        on_start = MagicMock()
        listener = HotkeyListener(on_start=on_start)

        from pynput.keyboard import Key

        listener._on_press(Key.f9)
        on_start.assert_not_called()

    @patch("pynput.keyboard.Listener")
    def test_start_creates_listener(self, mock_listener_class):
        listener = HotkeyListener()
        listener.start()
        mock_listener_class.assert_called_once()

    @patch("pynput.keyboard.Listener")
    def test_stop(self, mock_listener_class):
        listener = HotkeyListener()
        mock_instance = MagicMock()
        mock_listener_class.return_value = mock_instance
        listener.start()
        listener.stop()
        mock_instance.stop.assert_called_once()
