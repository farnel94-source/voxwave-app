"""Tests pour src/gui/tray_icon.py et src/gui/icons.py."""

import sys
from unittest.mock import patch, MagicMock

import pytest
from PIL import ImageChops

from src.gui.icons import create_icon, STATE_COLORS


@pytest.fixture(scope="module")
def qapp():
    """Cree une QApplication pour les tests."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestIcons:
    """Tests generation d'icones."""

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

    def test_create_icon_idle_has_large_visual_coverage(self):
        """Evite une icone visuellement minuscule (marge transparente trop grande)."""
        size = 64
        img = create_icon("idle", size=size)
        alpha = img.split()[-1]
        bbox = alpha.getbbox()
        assert bbox is not None
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        assert width > int(size * 0.70)
        assert height > int(size * 0.70)

    @pytest.mark.parametrize("state", ["recording", "processing", "error"])
    def test_create_icon_state_has_badge_in_bottom_right(self, state):
        """Les etats non-idle doivent ajouter un badge visible en bas a droite."""
        size = 64
        idle = create_icon("idle", size=size)
        with_badge = create_icon(state, size=size)
        diff = ImageChops.difference(idle, with_badge)
        bbox = diff.getbbox()
        assert bbox is not None
        # Le badge doit apparaitre dans la moitie basse-droite de l'icone
        assert bbox[0] >= size // 2
        assert bbox[1] >= size // 2

    def test_state_colors_all_present(self):
        for state in ("idle", "recording", "processing", "error"):
            assert state in STATE_COLORS

    def test_unknown_state_defaults_to_idle_color(self):
        img = create_icon("unknown")
        assert img.size == (64, 64)

    def test_create_qicon(self, qapp):
        from src.gui.icons import create_qicon
        icon = create_qicon("idle")
        assert not icon.isNull()


class TestTrayIcon:
    """Tests TrayIcon (PySide6)."""

    def test_init(self):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        assert tray._state == "idle"
        assert tray._is_recording is False

    def test_set_state_recording(self, qapp):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        tray.setup()
        tray.set_state("recording")
        assert tray._state == "recording"
        assert tray._is_recording is True

    def test_set_state_idle(self, qapp):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        tray.setup()
        tray._is_recording = True
        tray.set_state("idle")
        assert tray._is_recording is False

    def test_show_notification_no_tray(self):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        # Should not raise when no tray
        tray.show_notification("Title", "Message")

    def test_toggle_start(self):
        from src.gui.tray_icon import TrayIcon
        on_start = MagicMock()
        tray = TrayIcon(on_start=on_start)
        tray._toggle_start()
        on_start.assert_called_once()
        assert tray._is_recording is True

    def test_toggle_stop(self):
        from src.gui.tray_icon import TrayIcon
        on_stop = MagicMock()
        tray = TrayIcon(on_stop=on_stop)
        tray._is_recording = True
        tray._toggle_stop()
        on_stop.assert_called_once()
        assert tray._is_recording is False

    def test_on_quit_click(self, qapp):
        from src.gui.tray_icon import TrayIcon
        on_quit = MagicMock()
        tray = TrayIcon(on_quit=on_quit)
        tray.setup()
        tray._on_quit_click()
        on_quit.assert_called_once()

    def test_stop(self, qapp):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        tray.setup()
        tray.stop()
        assert tray._tray is None

    def test_create_menu(self, qapp):
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        menu = tray._create_menu()
        assert menu is not None

    def test_reshow_recreates_tray(self, qapp):
        """setup() puis reshow() doit creer un nouvel objet QSystemTrayIcon."""
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        tray.setup()
        old_tray = tray._tray
        assert old_tray is not None
        tray.reshow()
        assert tray._tray is not None
        assert tray._tray is not old_tray

    def test_reshow_preserves_state(self, qapp):
        """reshow() doit conserver l'etat visuel (ex: recording)."""
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        tray.setup()
        tray.set_state("recording")
        tray.reshow()
        assert tray._state == "recording"

    def test_reshow_without_setup(self):
        """reshow() sans setup() prealable ne doit pas crash."""
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        # _tray est None, reshow() doit quand meme fonctionner
        tray.reshow()
        assert tray._tray is not None

    def test_stop_cleanup(self, qapp):
        """stop() doit mettre _tray a None et cacher l'icone."""
        from src.gui.tray_icon import TrayIcon
        tray = TrayIcon()
        tray.setup()
        assert tray._tray is not None
        tray.stop()
        assert tray._tray is None
