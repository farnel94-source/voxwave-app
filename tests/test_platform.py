"""Tests pour la detection de plateforme."""

import sys
from unittest.mock import patch

import pytest

from src.utils.platform import get_display_server


class TestGetDisplayServer:
    """Tests get_display_server()."""

    @patch.object(sys, "platform", "win32")
    def test_windows(self):
        assert get_display_server() == "windows"

    @patch.object(sys, "platform", "darwin")
    def test_darwin(self):
        assert get_display_server() == "darwin"

    @patch.object(sys, "platform", "linux")
    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "wayland"}, clear=False)
    def test_wayland(self):
        assert get_display_server() == "wayland"

    @patch.object(sys, "platform", "linux")
    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "x11"}, clear=False)
    def test_x11_session_type(self):
        assert get_display_server() == "x11"

    @patch.object(sys, "platform", "linux")
    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "", "DISPLAY": ":0"}, clear=False)
    def test_x11_display_env(self):
        assert get_display_server() == "x11"

    @patch.object(sys, "platform", "linux")
    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "", "DISPLAY": ""}, clear=False)
    def test_unknown(self):
        result = get_display_server()
        # Peut etre x11 si DISPLAY est set par le systeme
        assert result in ("unknown", "x11")


class TestHotkeyListenerBackend:
    """Tests de la selection du backend hotkey."""

    @patch.object(sys, "platform", "win32")
    def test_windows_uses_pynput(self):
        from src.hotkey.listener import HotkeyListener
        assert HotkeyListener._detect_backend() == "pynput"

    @patch.object(sys, "platform", "darwin")
    def test_darwin_uses_pynput(self):
        from src.hotkey.listener import HotkeyListener
        assert HotkeyListener._detect_backend() == "pynput"


class TestTextInjectorBackend:
    """Tests de la selection du backend d'injection."""

    @patch("platform.system", return_value="Windows")
    def test_windows_injector(self, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")
        assert injector.os_name == "windows"

    @patch("platform.system", return_value="Linux")
    @patch("src.utils.platform.get_display_server", return_value="wayland")
    @patch("shutil.which", return_value=None)
    def test_linux_wayland_injector(self, mock_which, mock_display, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")
        assert injector._display_server == "wayland"

    @patch("platform.system", return_value="Linux")
    @patch("src.utils.platform.get_display_server", return_value="x11")
    @patch("shutil.which", return_value="/usr/bin/xdotool")
    def test_linux_x11_injector(self, mock_which, mock_display, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")
        assert injector._display_server == "x11"


class TestTextInjectorWayland:
    """Tests d'injection Wayland (mock subprocess)."""

    @patch("platform.system", return_value="Linux")
    @patch("src.utils.platform.get_display_server", return_value="wayland")
    @patch("shutil.which", return_value="/usr/bin/wtype")
    @patch("subprocess.run")
    @patch("pyperclip.paste", return_value="original")
    @patch("pyperclip.copy")
    def test_paste_wayland_calls_wtype(self, mock_copy, mock_paste, mock_run, mock_which, mock_display, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")
        injector._inject_paste_wayland("test text")
        mock_copy.assert_any_call("test text")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "wtype" in args[0]


class TestTextInjectorX11:
    """Tests d'injection X11 (mock subprocess)."""

    @patch("platform.system", return_value="Linux")
    @patch("src.utils.platform.get_display_server", return_value="x11")
    @patch("shutil.which", return_value="/usr/bin/xdotool")
    @patch("subprocess.run")
    @patch("pyperclip.paste", return_value="original")
    @patch("pyperclip.copy")
    def test_paste_x11_calls_xdotool(self, mock_copy, mock_paste, mock_run, mock_which, mock_display, mock_sys):
        from src.injection.keyboard import TextInjector
        injector = TextInjector(mode="paste")
        injector._inject_paste_x11("test text")
        mock_copy.assert_any_call("test text")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "xdotool" in args[0]
