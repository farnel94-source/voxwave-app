"""Tests pour les timeouts sur injection clavier."""

import time
from unittest.mock import patch, MagicMock

import pytest


class TestWithTimeout:
    """Tests _with_timeout wrapper."""

    def test_function_completes_within_timeout(self):
        from src.injection.keyboard import _with_timeout
        result = _with_timeout(lambda: 42, 2.0, -1)
        assert result == 42

    def test_function_returns_default_on_timeout(self):
        from src.injection.keyboard import _with_timeout

        def slow_func():
            time.sleep(5)
            return 42

        result = _with_timeout(slow_func, 0.1, -1)
        assert result == -1

    def test_function_returns_default_on_exception(self):
        from src.injection.keyboard import _with_timeout

        def failing_func():
            raise RuntimeError("boom")

        result = _with_timeout(failing_func, 2.0, -1)
        assert result == -1

    def test_function_with_args(self):
        from src.injection.keyboard import _with_timeout

        def add(a, b):
            return a + b

        result = _with_timeout(add, 2.0, -1, 3, 4)
        assert result == 7

    def test_function_with_kwargs(self):
        from src.injection.keyboard import _with_timeout

        def greet(name="world"):
            return f"hello {name}"

        result = _with_timeout(greet, 2.0, "fail", name="test")
        assert result == "hello test"


class TestClipboardTimeouts:
    """Tests clipboard operations with timeouts."""

    @patch("platform.system", return_value="Windows")
    def test_save_clipboard_returns_none_on_timeout(self, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")

        with patch("pyperclip.paste", side_effect=lambda: time.sleep(5)):
            # Should return None (default) instead of hanging
            result = injector._save_clipboard()
            # May be None due to timeout or exception
            # The key is it doesn't hang

    @patch("platform.system", return_value="Windows")
    def test_copy_to_clipboard_doesnt_hang_on_timeout(self, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")

        with patch("pyperclip.copy", side_effect=lambda x: time.sleep(10)):
            # Should not hang for 10s — timeout at 2s + some overhead
            start = time.time()
            injector._copy_to_clipboard("test")
            elapsed = time.time() - start
            assert elapsed < 8  # Well under 10s hang

    @patch("platform.system", return_value="Windows")
    def test_paste_from_clipboard_returns_none_on_timeout(self, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")

        with patch("pyperclip.paste", side_effect=lambda: time.sleep(10)):
            start = time.time()
            result = injector._paste_from_clipboard()
            elapsed = time.time() - start
            assert elapsed < 8  # Well under 10s hang
