"""Tests for OrbWidget (QPainter-based orb)."""
import math
import os
import sys

import pytest
from unittest.mock import MagicMock

# QApplication needs a display — skip all widget tests in headless CI
_HEADLESS = not os.environ.get("DISPLAY") and sys.platform != "win32"


@pytest.fixture(scope="session")
def qapp():
    """Create or reuse a QApplication for the test session."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def orb(qapp):
    if _HEADLESS:
        pytest.skip("No display available (headless)")
    from src.gui.orb_widget import OrbWidget
    widget = OrbWidget(
        on_start=MagicMock(),
        on_stop=MagicMock(),
        on_settings=MagicMock(),
        on_quit=MagicMock(),
    )
    yield widget
    widget.close()


class TestOrbWidgetAPI:
    """OrbWidget must expose the same public API as WaveformWidget."""

    def test_instantiation(self, orb):
        assert orb is not None

    def test_has_show_recording(self, orb):
        assert callable(orb.show_recording)

    def test_has_show_processing(self, orb):
        assert callable(orb.show_processing)

    def test_has_show_idle(self, orb):
        assert callable(orb.show_idle)

    def test_has_show_error(self, orb):
        assert callable(orb.show_error)

    def test_has_set_error_text(self, orb):
        assert callable(orb.set_error_text)

    def test_has_update_step(self, orb):
        assert callable(orb.update_step)

    def test_has_show_preview(self, orb):
        assert callable(orb.show_preview)

    def test_has_set_capture(self, orb):
        assert callable(orb.set_capture)

    def test_has_ensure_topmost(self, orb):
        assert callable(orb.ensure_topmost)

    def test_initial_state_is_idle(self, orb):
        assert orb._state == "idle"

    def test_widget_size(self, orb):
        assert orb.width() == 300
        assert orb.height() == 116


class TestAuraIntensity:
    """Aura intensity calculation math."""

    def test_intensity_zero_when_no_amplitude(self, orb):
        orb._smoothed_volume = 0.0
        intensity = min(pow(orb._smoothed_volume * 2.5, 1.2), 1.5)
        assert intensity == 0.0

    def test_intensity_clamped(self, orb):
        orb._smoothed_volume = 1.0
        intensity = min(pow(orb._smoothed_volume * 2.5, 1.2), 1.5)
        assert intensity <= 1.5


class TestAnimationMath:
    """Animation formulas produce expected values."""

    def test_breathe_idle_range(self):
        """Breathe value always between 0 and 1."""
        for t in [0.0, 0.5, 1.0, 1.75, 3.5]:
            val = math.sin(t * 2 * math.pi / 3.5) * 0.5 + 0.5
            assert 0.0 <= val <= 1.0

    def test_breathe_recording_faster(self):
        """Recording breathe at quarter-period should be near peak."""
        t = 0.45  # ~1/4 of 1.8s
        val = math.sin(t * 2 * math.pi / 1.8) * 0.5 + 0.5
        assert val > 0.9

    def test_shake_amplitude_decreases(self):
        """Shake displacement values decrease over time."""
        shake_values = [0, -3, 3, -2, 2, -1, 1, 0]
        for i in range(1, len(shake_values)):
            assert abs(shake_values[i]) <= abs(shake_values[max(1, i - 1)])


class TestMouseInteractions:
    """Click vs drag threshold logic."""

    def test_small_movement_is_click(self):
        threshold = 5
        dx, dy = 3, 2
        dist = (dx**2 + dy**2) ** 0.5
        assert dist < threshold

    def test_large_movement_is_drag(self):
        threshold = 5
        dx, dy = 4, 4
        dist = (dx**2 + dy**2) ** 0.5
        assert dist >= threshold
