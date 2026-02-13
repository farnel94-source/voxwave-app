"""Tests pour src/injection/keyboard.py."""

from unittest.mock import patch, MagicMock

import pytest


class TestTextInjector:
    """Tests TextInjector."""

    @patch("platform.system", return_value="Windows")
    def test_init_paste_mode(self, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")
        assert injector.mode == "paste"

    @patch("platform.system", return_value="Windows")
    def test_init_type_mode(self, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="type")
        assert injector.mode == "type"

    @patch("platform.system", return_value="Windows")
    def test_inject_empty_does_nothing(self, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector()
        injector.inject("")

    @patch("platform.system", return_value="Windows")
    @patch("src.injection.keyboard.TextInjector._inject_paste")
    def test_inject_paste_mode(self, mock_paste, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")
        injector.inject("hello")
        mock_paste.assert_called_once_with("hello")

    @patch("platform.system", return_value="Windows")
    @patch("src.injection.keyboard.TextInjector._inject_type")
    def test_inject_type_mode(self, mock_type, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="type")
        injector.inject("hello")
        mock_type.assert_called_once_with("hello")

    @patch("platform.system", return_value="Windows")
    @patch("src.injection.keyboard.TextInjector._inject_paste_win32")
    def test_inject_paste_windows(self, mock_win32, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")
        injector._inject_paste("hello")
        mock_win32.assert_called_once_with("hello")

    @patch("platform.system", return_value="Windows")
    @patch("keyboard.send")
    @patch("pyperclip.paste", return_value="hello world")
    @patch("pyperclip.copy")
    def test_inject_paste_win32_full(self, mock_copy, mock_paste, mock_kb_send, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")
        injector._inject_paste_win32("hello world")
        mock_copy.assert_called_with("hello world")
        mock_kb_send.assert_called_once_with('ctrl+v')

    @patch("platform.system", return_value="Windows")
    @patch("keyboard.send")
    @patch("pyperclip.paste", return_value="mismatch")
    @patch("pyperclip.copy")
    def test_inject_paste_win32_clipboard_mismatch_retries(self, mock_copy, mock_paste, mock_kb_send, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")
        injector._inject_paste_win32("hello world")
        # 2 copy attempts (initial + retry) + 1 restore = 3
        assert mock_copy.call_count == 3
        mock_kb_send.assert_called_once_with('ctrl+v')

    @patch("platform.system", return_value="Windows")
    @patch("keyboard.write")
    def test_inject_type(self, mock_write, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="type")
        injector._inject_type("hello")
        mock_write.assert_called_once_with("hello", delay=0.01)


class TestTextInjectorWayland:
    """Tests injection Wayland."""

    @patch("platform.system", return_value="Linux")
    @patch("src.utils.platform.get_display_server", return_value="wayland")
    @patch("shutil.which", return_value="/usr/bin/wtype")
    @patch("subprocess.run")
    @patch("pyperclip.paste", return_value="original")
    @patch("pyperclip.copy")
    def test_wayland_paste(self, mock_copy, mock_paste, mock_run, mock_which, mock_display, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")
        injector._inject_paste_wayland("test")
        mock_copy.assert_any_call("test")
        mock_run.assert_called_once()


class TestTextInjectorX11:
    """Tests injection X11."""

    @patch("platform.system", return_value="Linux")
    @patch("src.utils.platform.get_display_server", return_value="x11")
    @patch("shutil.which", return_value="/usr/bin/xdotool")
    @patch("subprocess.run")
    @patch("pyperclip.paste", return_value="original")
    @patch("pyperclip.copy")
    def test_x11_paste(self, mock_copy, mock_paste, mock_run, mock_which, mock_display, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")
        injector._inject_paste_x11("test")
        mock_copy.assert_any_call("test")
        mock_run.assert_called_once()
