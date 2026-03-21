"""Test: le free tier ne doit PAS bloquer les transcriptions locales.

Bug: increment_usage() retourne False quand la limite est atteinte,
bloquant TOUT y compris Whisper local + regex. Seul le cloud devrait
etre limite.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.licensing.validator import LicenseValidator


class TestFreeTierLocalNotBlocked:
    """Le local (Whisper + regex) doit toujours fonctionner, meme apres la limite."""

    def test_local_transcription_allowed_after_daily_limit(self):
        """Un utilisateur free tier qui a epuise sa limite cloud
        doit pouvoir continuer en local."""
        validator = LicenseValidator(free_daily_limit=5)

        # Simuler 5 utilisations (limite atteinte)
        validator.storage = MagicMock()
        validator.storage.get_daily_usage.return_value = 5

        # increment_usage pour du LOCAL ne devrait PAS bloquer
        result = validator.increment_usage_for_provider("local")
        assert result is True, (
            "Le local ne devrait JAMAIS etre bloque par le free tier"
        )

    @patch("src.licensing.validator._is_dev_mode", return_value=False)
    def test_cloud_transcription_blocked_after_daily_limit(self, mock_dev):
        """Un utilisateur free tier qui a epuise sa limite cloud
        doit etre bloque pour le cloud."""
        validator = LicenseValidator(free_daily_limit=5)

        validator.storage = MagicMock()
        validator.storage.get_daily_usage.return_value = 5
        validator.storage.load_license.return_value = None

        # increment_usage pour du CLOUD devrait bloquer
        result = validator.increment_usage_for_provider("cloud")
        assert result is False, (
            "Le cloud devrait etre bloque quand le free tier est epuise"
        )

    def test_cloud_allowed_under_limit(self):
        """Sous la limite, le cloud doit fonctionner."""
        validator = LicenseValidator(free_daily_limit=50)

        validator.storage = MagicMock()
        validator.storage.get_daily_usage.return_value = 10
        validator.storage.get_usage.return_value = 10

        result = validator.increment_usage_for_provider("cloud")
        assert result is True

    def test_licensed_user_always_allowed(self):
        """Un utilisateur avec licence peut tout faire, cloud ou local."""
        validator = LicenseValidator(free_daily_limit=5)

        validator.storage = MagicMock()
        validator.storage.get_daily_usage.return_value = 999

        with patch.object(validator, "is_licensed", return_value=True):
            assert validator.increment_usage_for_provider("cloud") is True
            assert validator.increment_usage_for_provider("local") is True
