"""Tests pour le module window_detector."""
from unittest.mock import patch, MagicMock
from src.utils.window_detector import get_active_exe, get_app_profile


def test_get_app_profile_code():
    assert get_app_profile("code.exe") == "code"
    assert get_app_profile("Code") == "code"
    assert get_app_profile("pycharm64.exe") == "code"
    assert get_app_profile("windowsterminal.exe") == "code"


def test_get_app_profile_casual():
    assert get_app_profile("slack.exe") == "casual"
    assert get_app_profile("discord.exe") == "casual"
    assert get_app_profile("Telegram.exe") == "casual"


def test_get_app_profile_email():
    assert get_app_profile("OUTLOOK.EXE") == "email"
    assert get_app_profile("thunderbird.exe") == "email"


def test_get_app_profile_document():
    assert get_app_profile("WINWORD.EXE") == "document"
    assert get_app_profile("soffice.exe") == "document"


def test_get_app_profile_default():
    assert get_app_profile("chrome.exe") == "default"
    assert get_app_profile("unknown_app.exe") == "default"
    assert get_app_profile("") == "default"
    assert get_app_profile(None) == "default"


def test_get_active_exe_windows():
    """Test Windows path avec mock ctypes."""
    import sys
    if sys.platform != "win32":
        return  # skip sur Linux
    with patch("ctypes.windll") as mock_windll:
        mock_windll.user32.GetForegroundWindow.return_value = 12345
        # Test juste que la fonction ne crash pas
        result = get_active_exe()
        assert isinstance(result, str)


def test_get_active_exe_linux():
    """Test Linux path avec mock subprocess."""
    import sys
    if sys.platform != "linux":
        return  # skip sur Windows
    with patch("subprocess.check_output") as mock_cmd:
        mock_cmd.side_effect = [b"12345\n", b"67890\n", b"VS Code\n"]
        with patch("builtins.open", MagicMock(return_value=MagicMock(
            __enter__=lambda s, *a: s,
            __exit__=lambda s, *a: None,
            read=lambda: "code\n"
        ))):
            result = get_active_exe()
            assert isinstance(result, str)
