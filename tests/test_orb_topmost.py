"""Tests pour le bug: orb perd son statut always-on-top sur Windows.

Root cause: _check_orb_health() ne restaurait pas HWND_TOPMOST et ne faisait
rien quand l'orb était visible (mais derrière d'autres fenêtres).

Fix: ensure_topmost() via Win32 SetWindowPos, appelé à chaque tick du health check.
"""

from unittest.mock import MagicMock, patch


class TestOrbHealthCheckRestoresTopmost:
    """Le health check doit toujours appeler ensure_topmost()."""

    def _make_app(self, visible: bool = True, activation: str = "both"):
        app = MagicMock()
        app.config = {"activation_method": activation}
        app.waveform = MagicMock()
        app.waveform.isVisible.return_value = visible
        return app

    def test_visible_orb_gets_topmost_restored(self):
        """Orb visible mais potentiellement derrière → ensure_topmost() appelé."""
        app = self._make_app(visible=True)

        # Import et appel direct de la méthode non-bound
        with patch.dict("sys.modules", {"sentry_sdk": MagicMock()}):
            from src.app import VoxWave
            VoxWave._check_orb_health(app)

        app.waveform.ensure_topmost.assert_called_once()
        app.waveform.raise_.assert_called_once()
        # show() pas appelé car déjà visible
        app.waveform.show.assert_not_called()

    def test_invisible_orb_gets_reshown_and_topmost(self):
        """Orb invisible → show() + raise_() + ensure_topmost()."""
        app = self._make_app(visible=False)

        with patch.dict("sys.modules", {"sentry_sdk": MagicMock()}):
            from src.app import VoxWave
            VoxWave._check_orb_health(app)

        app.waveform.show.assert_called_once()
        app.waveform.raise_.assert_called_once()
        app.waveform.ensure_topmost.assert_called_once()

    def test_hotkey_mode_skips_health_check(self):
        """En mode hotkey, le health check ne fait rien."""
        app = self._make_app(activation="hotkey")

        with patch.dict("sys.modules", {"sentry_sdk": MagicMock()}):
            from src.app import VoxWave
            VoxWave._check_orb_health(app)

        app.waveform.show.assert_not_called()
        app.waveform.raise_.assert_not_called()
        app.waveform.ensure_topmost.assert_not_called()
