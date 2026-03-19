"""Tests pour le garde-fou de délai dans replace_with_clean.

Bug : le profil 'email' (prompt LLM plus lourd) provoque un nettoyage
de ~2.5s, dépassant l'ancien seuil de 1.5s → le remplacement était ignoré.
Fix : seuil augmenté à 5.0s.
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


def _slow_generator(text: str, delay: float):
    """Simule un stream OpenAI lent (comme le profil email)."""
    time.sleep(delay)
    yield text


class TestReplaceTimeout:
    """Le garde-fou de délai accepte les profils lents mais rejette les extrêmes."""

    @patch("src.injection.progressive_injector.pyperclip", create=True)
    def test_email_profile_accepted(self, mock_pyperclip, injector):
        """Un nettoyage email de 2s doit passer (seuil = 5.0s)."""
        raw = "texte brut de test"
        clean = "Texte propre de test."
        mock_pyperclip.paste.return_value = ""

        injector._inject_time = time.monotonic()
        injector._user_acted = False

        injector.replace_with_clean(raw, _slow_generator(clean, 2.0))

        injector._send_backspaces.assert_called_once()

    @patch("src.injection.progressive_injector.pyperclip", create=True)
    def test_fast_cleanup_works(self, mock_pyperclip, injector):
        """Un nettoyage rapide (<1s) passe toujours."""
        raw = "texte brut"
        clean = "Texte propre."
        mock_pyperclip.paste.return_value = ""

        injector._inject_time = time.monotonic()
        injector._user_acted = False

        injector.replace_with_clean(raw, _slow_generator(clean, 0.3))

        injector._send_backspaces.assert_called_once()

    @patch("src.injection.progressive_injector.pyperclip", create=True)
    def test_very_long_delay_rejected(self, mock_pyperclip, injector):
        """Un délai > 5s est rejeté (sécurité)."""
        raw = "texte brut"
        clean = "Texte propre."

        injector._inject_time = time.monotonic()
        injector._user_acted = False

        injector.replace_with_clean(raw, _slow_generator(clean, 5.5))

        injector._send_backspaces.assert_not_called()

    @patch("src.injection.progressive_injector.pyperclip", create=True)
    def test_user_action_still_blocks(self, mock_pyperclip, injector):
        """Le garde-fou action utilisateur continue de bloquer."""
        raw = "texte brut"
        clean = "Texte propre."
        mock_pyperclip.paste.return_value = ""

        injector._inject_time = time.monotonic()
        injector._user_acted = True  # L'utilisateur a tapé/cliqué

        injector.replace_with_clean(raw, _slow_generator(clean, 0.1))

        injector._send_backspaces.assert_not_called()
