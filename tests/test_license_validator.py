"""Tests pour src/licensing/validator.py et src/licensing/storage.py."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.utils.exceptions import LicenseError


class TestLicenseStorage:
    """Tests LicenseStorage."""

    def test_save_and_load_license(self, tmp_path):
        with patch("src.licensing.storage.VOXWAVE_DIR", tmp_path), \
             patch("src.licensing.storage.LICENSE_FILE", tmp_path / "license.enc"), \
             patch("src.licensing.storage.KEY_FILE", tmp_path / ".key"), \
             patch("src.licensing.storage.USAGE_FILE", tmp_path / "usage.json"):
            from src.licensing.storage import LicenseStorage

            storage = LicenseStorage()
            data = {"license_key": "test-123", "instance_id": "abc"}
            storage.save_license(data)
            loaded = storage.load_license()
            assert loaded["license_key"] == "test-123"

    def test_load_license_empty(self, tmp_path):
        with patch("src.licensing.storage.VOXWAVE_DIR", tmp_path), \
             patch("src.licensing.storage.LICENSE_FILE", tmp_path / "license.enc"), \
             patch("src.licensing.storage.KEY_FILE", tmp_path / ".key"), \
             patch("src.licensing.storage.USAGE_FILE", tmp_path / "usage.json"):
            from src.licensing.storage import LicenseStorage

            storage = LicenseStorage()
            assert storage.load_license() is None

    def test_delete_license(self, tmp_path):
        with patch("src.licensing.storage.VOXWAVE_DIR", tmp_path), \
             patch("src.licensing.storage.LICENSE_FILE", tmp_path / "license.enc"), \
             patch("src.licensing.storage.KEY_FILE", tmp_path / ".key"), \
             patch("src.licensing.storage.USAGE_FILE", tmp_path / "usage.json"):
            from src.licensing.storage import LicenseStorage

            storage = LicenseStorage()
            storage.save_license({"key": "test"})
            storage.delete_license()
            assert storage.load_license() is None

    def test_usage_counter(self, tmp_path):
        with patch("src.licensing.storage.VOXWAVE_DIR", tmp_path), \
             patch("src.licensing.storage.USAGE_FILE", tmp_path / "usage.json"):
            from src.licensing.storage import LicenseStorage

            assert LicenseStorage.get_usage() == 0
            LicenseStorage.increment_usage()
            assert LicenseStorage.get_usage() == 1
            LicenseStorage.increment_usage()
            assert LicenseStorage.get_usage() == 2

    def test_daily_usage_counter(self, tmp_path):
        with patch("src.licensing.storage.VOXWAVE_DIR", tmp_path), \
             patch("src.licensing.storage.USAGE_FILE", tmp_path / "usage.json"):
            from src.licensing.storage import LicenseStorage

            assert LicenseStorage.get_daily_usage() == 0
            LicenseStorage.increment_usage()
            assert LicenseStorage.get_daily_usage() == 1
            LicenseStorage.increment_usage()
            assert LicenseStorage.get_daily_usage() == 2

    def test_daily_usage_resets_on_new_day(self, tmp_path):
        with patch("src.licensing.storage.VOXWAVE_DIR", tmp_path), \
             patch("src.licensing.storage.USAGE_FILE", tmp_path / "usage.json"):
            from src.licensing.storage import LicenseStorage

            # Simulate usage from a different day
            data = {"count": 5, "daily_count": 5, "daily_date": "2024-01-01"}
            (tmp_path / "usage.json").write_text(json.dumps(data))
            # Daily usage should be 0 (different day)
            assert LicenseStorage.get_daily_usage() == 0
            # Total usage should still be 5
            assert LicenseStorage.get_usage() == 5


class TestLicenseValidator:
    """Tests LicenseValidator."""

    @patch("src.licensing.validator._is_dev_mode", return_value=False)
    def test_can_transcribe_under_daily_limit(self, _):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator(free_daily_limit=10)
        validator.storage = MagicMock()
        validator.storage.get_daily_usage.return_value = 5
        validator.storage.load_license.return_value = None

        assert validator.can_transcribe() is True

    @patch("src.licensing.validator._is_dev_mode", return_value=False)
    def test_cannot_transcribe_over_daily_limit(self, _):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator(free_daily_limit=10)
        validator.storage = MagicMock()
        validator.storage.get_daily_usage.return_value = 10
        validator.storage.load_license.return_value = None

        assert validator.can_transcribe() is False

    def test_licensed_user_always_can_transcribe(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator(free_daily_limit=10)
        validator.storage = MagicMock()
        validator.storage.get_daily_usage.return_value = 99999
        validator.storage.load_license.return_value = {"license_key": "valid-key"}
        validator.client = MagicMock()
        validator.client.validate_license.return_value = {"valid": True}

        assert validator.can_transcribe() is True

    @patch("src.licensing.validator._is_dev_mode", return_value=False)
    def test_increment_usage_returns_false_at_daily_limit(self, _):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator(free_daily_limit=5)
        validator.storage = MagicMock()
        validator.storage.load_license.return_value = None
        validator.storage.get_daily_usage.return_value = 5

        assert validator.increment_usage() is False

    @patch("src.licensing.validator._is_dev_mode", return_value=False)
    def test_increment_usage_returns_true_under_daily_limit(self, _):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator(free_daily_limit=50)
        validator.storage = MagicMock()
        validator.storage.load_license.return_value = None
        validator.storage.get_daily_usage.return_value = 3

        assert validator.increment_usage() is True
        validator.storage.increment_usage.assert_called_once()

    def test_activate_license(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator()
        validator.client = MagicMock()
        validator.client.activate_license.return_value = {
            "activated": True,
            "instance": {"id": "inst-123"},
        }
        validator.storage = MagicMock()

        result = validator.activate_license("key-abc")
        assert result is True
        validator.storage.save_license.assert_called_once()

    def test_activate_license_failure(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator()
        validator.client = MagicMock()
        validator.client.activate_license.side_effect = LicenseError("Invalid key")

        with pytest.raises(LicenseError):
            validator.activate_license("bad-key")

    @patch("src.licensing.validator._is_dev_mode", return_value=False)
    def test_get_usage_info(self, _):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator(free_daily_limit=50)
        validator.storage = MagicMock()
        validator.storage.load_license.return_value = None
        validator.storage.get_usage.return_value = 42
        validator.storage.get_daily_usage.return_value = 7

        info = validator.get_usage_info()
        assert info["licensed"] is False
        assert info["usage"] == 42
        assert info["daily_usage"] == 7
        assert info["daily_limit"] == 50
        assert info["remaining_today"] == 43

    def test_offline_validation_trusts_cache(self):
        """Cache récent (<7 jours) doit être accepté offline."""
        import time
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator()
        validator.storage = MagicMock()
        validator.storage.load_license.return_value = {"license_key": "key-123"}
        validator.client = MagicMock()
        validator.client.validate_license.side_effect = LicenseError("Network error")
        # Simuler un cache récent (validé il y a 1 heure)
        validator._cached_valid = True
        validator._cache_time = time.time() - 3600

        assert validator.is_licensed() is True

    def test_offline_validation_rejects_expired_cache(self):
        """Cache expiré (>7 jours) doit être rejeté offline → free tier."""
        import time
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator()
        validator.storage = MagicMock()
        validator.storage.load_license.return_value = {"license_key": "key-123"}
        validator.client = MagicMock()
        validator.client.validate_license.side_effect = LicenseError("Network error")
        # Simuler un cache vieux de 8 jours
        validator._cached_valid = True
        validator._cache_time = time.time() - (8 * 86400)

        assert validator.is_licensed() is False

    @patch("src.licensing.validator._is_dev_mode", return_value=False)
    def test_get_transcription_provider_free(self, _):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator()
        validator.storage = MagicMock()
        validator.storage.load_license.return_value = None
        assert validator.get_transcription_provider() == "local"

    def test_get_transcription_provider_paid(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator()
        validator._cached_valid = True
        validator._cache_time = __import__("time").time()
        assert validator.get_transcription_provider() == "hybrid"

    @patch("src.licensing.validator._is_dev_mode", return_value=False)
    def test_get_cleaning_provider_free(self, _):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator()
        validator.storage = MagicMock()
        validator.storage.load_license.return_value = None
        assert validator.get_cleaning_provider() == "local"

    def test_get_cleaning_provider_paid(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator()
        validator._cached_valid = True
        validator._cache_time = __import__("time").time()
        assert validator.get_cleaning_provider() == "hybrid"

    def test_days_remaining_no_license(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator()
        validator.storage = MagicMock()
        validator.storage.load_license.return_value = None
        assert validator.days_remaining() is None

    def test_days_remaining_lifetime(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator()
        validator.storage = MagicMock()
        validator.storage.load_license.return_value = {"license_key": "k"}
        assert validator.days_remaining() is None
