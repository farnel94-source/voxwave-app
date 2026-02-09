"""Tests pour src/gui/tray_icon.py et src/gui/icons.py."""

from unittest.mock import patch, MagicMock

import pytest

from src.gui.icons import create_icon, STATE_COLORS


class TestIcons:
    """Tests génération d'icônes."""

    def test_create_icon_idle(self):
        img = create_icon("idle")
        assert img.size == (64, 64)
        assert img.mode == "RGBA"

    def test_create_icon_recording(self):
        img = create_icon("recording")
        assert img.size == (64, 64)

    def test_create_icon_processing(self):
        img = create_icon("processing")
        assert img.size == (64, 64)

    def test_create_icon_error(self):
        img = create_icon("error")
        assert img.size == (64, 64)

    def test_create_icon_custom_size(self):
        img = create_icon("idle", size=128)
        assert img.size == (128, 128)

    def test_state_colors_all_present(self):
        for state in ("idle", "recording", "processing", "error"):
            assert state in STATE_COLORS

    def test_unknown_state_defaults_to_idle_color(self):
        img = create_icon("unknown")
        # Should not raise, falls back to idle color
        assert img.size == (64, 64)


class TestTrayIcon:
    """Tests TrayIcon."""

    def test_init(self):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        assert tray._state == "idle"
        assert tray._is_recording is False

    def test_set_state(self):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        tray._icon = MagicMock()
        tray.set_state("recording")
        assert tray._state == "recording"
        assert tray._is_recording is True
        tray._icon.update_menu.assert_called()

    def test_set_state_idle(self):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        tray._icon = MagicMock()
        tray._is_recording = True
        tray.set_state("idle")
        assert tray._is_recording is False

    def test_show_notification(self):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        tray._icon = MagicMock()
        tray.show_notification("Title", "Message")
        tray._icon.notify.assert_called_once_with("Message", "Title")

    def test_show_notification_no_icon(self):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        # Should not raise when no icon
        tray.show_notification("Title", "Message")

    def test_toggle_recording_start(self):
        from src.gui.tray_icon import TrayIcon
        on_start = MagicMock()
        tray = TrayIcon(on_start=on_start)
        tray._is_recording = False
        tray._toggle_recording(None, None)
        on_start.assert_called_once()
        assert tray._is_recording is True

    def test_toggle_recording_stop(self):
        from src.gui.tray_icon import TrayIcon
        on_stop = MagicMock()
        tray = TrayIcon(on_stop=on_stop)
        tray._is_recording = True
        tray._toggle_recording(None, None)
        on_stop.assert_called_once()
        assert tray._is_recording is False

    def test_on_quit_click(self):
        from src.gui.tray_icon import TrayIcon
        on_quit = MagicMock()
        tray = TrayIcon(on_quit=on_quit)
        tray._icon = MagicMock()
        tray._on_quit_click(None, None)
        on_quit.assert_called_once()

    def test_stop(self):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        tray._icon = MagicMock()
        tray.stop()
        assert tray._icon is None

    def test_create_menu(self):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        menu = tray._create_menu()
        assert menu is not None
