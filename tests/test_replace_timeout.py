"""Tests pour le timeout dynamique de replace_with_clean.

Le timeout s'adapte à la longueur du texte :
timeout = 5s base + 10ms/char, cap 30s.
"""

import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def injector():
    """Crée un ProgressiveInjector avec un TextInjector mocké."""
    from src.injection.progressive_injector import ProgressiveInjector

    mock_text_injector = MagicMock()
    inj = ProgressiveInjector(mock_text_injector)
    inj._start_user_watch = MagicMock()
    inj._stop_user_watch = MagicMock()
    inj._send_backspaces = MagicMock()
    inj._send_ctrl_v = MagicMock()
    return inj


class TestComputeReplaceTimeout:
    """Tests unitaires pour la formule de timeout dynamique."""

    def test_short_text(self):
        """50 chars → 5.0 + 0.5 = 5.5s."""
        from src.injection.progressive_injector import _compute_replace_timeout
        assert _compute_replace_timeout(50) == pytest.approx(5.5, abs=0.01)

    def test_long_text(self):
        """1000 chars → 5.0 + 10.0 = 15.0s."""
        from src.injection.progressive_injector import _compute_replace_timeout
        assert _compute_replace_timeout(1000) == pytest.approx(15.0, abs=0.01)

    def test_cap_at_max(self):
        """5000 chars → 55.0 mais cap à 30.0s."""
        from src.injection.progressive_injector import _compute_replace_timeout
        assert _compute_replace_timeout(5000) == 30.0

    def test_zero_chars(self):
        """0 chars → minimum 5.0s."""
        from src.injection.progressive_injector import _compute_replace_timeout
        assert _compute_replace_timeout(0) == 5.0


class TestReplaceTimeout:
    """Tests d'intégration pour le garde-fou dynamique."""

    @patch("src.injection.progressive_injector.pyperclip", create=True)
    def test_short_text_accepted_within_timeout(self, mock_pyperclip, injector):
        """Texte court (18 chars), 2s écoulées → accepté (timeout ~5.2s)."""
        raw = "texte brut de test"
        clean = "Texte propre de test."
        mock_pyperclip.paste.return_value = ""

        injector._inject_time = time.monotonic() - 2.0
        injector._user_acted = False

        injector.replace_with_clean(raw, iter([clean]))

        injector._send_backspaces.assert_called_once()

    @patch("src.injection.progressive_injector.pyperclip", create=True)
    def test_short_text_rejected_past_timeout(self, mock_pyperclip, injector):
        """Texte court (10 chars), 6s écoulées → rejeté (timeout = 5.1s)."""
        raw = "texte brut"
        clean = "Texte propre."

        injector._inject_time = time.monotonic() - 6.0
        injector._user_acted = False

        injector.replace_with_clean(raw, iter([clean]))

        injector._send_backspaces.assert_not_called()

    @patch("src.injection.progressive_injector.pyperclip", create=True)
    def test_long_text_gets_more_time(self, mock_pyperclip, injector):
        """500 chars, 8s écoulées → accepté (timeout = 10.0s)."""
        raw = "a" * 500
        clean = "b" * 480
        mock_pyperclip.paste.return_value = ""

        injector._inject_time = time.monotonic() - 8.0
        injector._user_acted = False

        injector.replace_with_clean(raw, iter([clean]))

        injector._send_backspaces.assert_called_once()

    @patch("src.injection.progressive_injector.pyperclip", create=True)
    def test_long_text_still_has_limit(self, mock_pyperclip, injector):
        """500 chars, 12s écoulées → rejeté (timeout = 10.0s)."""
        raw = "a" * 500
        clean = "b" * 480

        injector._inject_time = time.monotonic() - 12.0
        injector._user_acted = False

        injector.replace_with_clean(raw, iter([clean]))

        injector._send_backspaces.assert_not_called()

    @patch("src.injection.progressive_injector.pyperclip", create=True)
    def test_very_long_text_capped_at_30s(self, mock_pyperclip, injector):
        """3000 chars, 25s écoulées → accepté (cap 30s)."""
        raw = "a" * 3000
        clean = "b" * 2900
        mock_pyperclip.paste.return_value = ""

        injector._inject_time = time.monotonic() - 25.0
        injector._user_acted = False

        injector.replace_with_clean(raw, iter([clean]))

        injector._send_backspaces.assert_called_once()

    @patch("src.injection.progressive_injector.pyperclip", create=True)
    def test_user_action_still_blocks(self, mock_pyperclip, injector):
        """Le garde-fou action utilisateur continue de bloquer."""
        raw = "texte brut"
        clean = "Texte propre."
        mock_pyperclip.paste.return_value = ""

        injector._inject_time = time.monotonic()
        injector._user_acted = True

        injector.replace_with_clean(raw, iter([clean]))

        injector._send_backspaces.assert_not_called()
