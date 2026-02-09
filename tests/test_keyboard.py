"""Tests pour src/injection/keyboard.py."""

from unittest.mock import patch, MagicMock

import pytest

from src.injection.keyboard import TextInjector


class TestTextInjector:
    """Tests TextInjector."""

    def test_init_paste_mode(self):
        injector = TextInjector(mode="paste")
        assert injector.mode == "paste"

    def test_init_type_mode(self):
        injector = TextInjector(mode="type")
        assert injector.mode == "type"

    def test_inject_empty_does_nothing(self):
        injector = TextInjector()
        injector.inject("")

    @patch("src.injection.keyboard.TextInjector._inject_paste")
    def test_inject_paste_mode(self, mock_paste):
        injector = TextInjector(mode="paste")
        injector.inject("hello")
        mock_paste.assert_called_once_with("hello")

    @patch("src.injection.keyboard.TextInjector._inject_type")
    def test_inject_type_mode(self, mock_type):
        injector = TextInjector(mode="type")
        injector.inject("hello")
        mock_type.assert_called_once_with("hello")

    @patch("src.injection.keyboard.TextInjector._inject_paste_win32")
    def test_inject_paste_windows(self, mock_win32):
        injector = TextInjector(mode="paste")
        injector.os_name = "windows"
        injector._inject_paste("hello")
        mock_win32.assert_called_once_with("hello")

    @patch("src.injection.keyboard.TextInjector._inject_paste_other")
    def test_inject_paste_linux(self, mock_other):
        injector = TextInjector(mode="paste")
        injector.os_name = "linux"
        injector._inject_paste("hello")
        mock_other.assert_called_once_with("hello")

    @patch("keyboard.send")
    @patch("pyperclip.paste", return_value="hello world")
    @patch("pyperclip.copy")
    def test_inject_paste_win32_full(self, mock_copy, mock_paste, mock_kb_send):
        injector = TextInjector(mode="paste")
        injector.os_name = "windows"
        injector._inject_paste_win32("hello world")
        mock_copy.assert_called_with("hello world")
        mock_kb_send.assert_called_once_with('ctrl+v')

    @patch("keyboard.send")
    @patch("pyperclip.paste", return_value="mismatch")
    @patch("pyperclip.copy")
    def test_inject_paste_win32_clipboard_mismatch_retries(self, mock_copy, mock_paste, mock_kb_send):
        injector = TextInjector(mode="paste")
        injector.os_name = "windows"
        injector._inject_paste_win32("hello world")
        # Should have called copy twice (initial + retry after mismatch)
        assert mock_copy.call_count == 2
        mock_kb_send.assert_called_once_with('ctrl+v')

    @patch("keyboard.write")
    def test_inject_type(self, mock_write):
        injector = TextInjector(mode="type")
        injector._inject_type("hello")
        mock_write.assert_called_once_with("hello", delay=0.01)
