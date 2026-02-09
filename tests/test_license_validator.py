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
        with patch("src.licensing.storage.VOXTOOL_DIR", tmp_path), \
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
        with patch("src.licensing.storage.VOXTOOL_DIR", tmp_path), \
             patch("src.licensing.storage.LICENSE_FILE", tmp_path / "license.enc"), \
             patch("src.licensing.storage.KEY_FILE", tmp_path / ".key"), \
             patch("src.licensing.storage.USAGE_FILE", tmp_path / "usage.json"):
            from src.licensing.storage import LicenseStorage

            storage = LicenseStorage()
            assert storage.load_license() is None

    def test_delete_license(self, tmp_path):
        with patch("src.licensing.storage.VOXTOOL_DIR", tmp_path), \
             patch("src.licensing.storage.LICENSE_FILE", tmp_path / "license.enc"), \
             patch("src.licensing.storage.KEY_FILE", tmp_path / ".key"), \
             patch("src.licensing.storage.USAGE_FILE", tmp_path / "usage.json"):
            from src.licensing.storage import LicenseStorage

            storage = LicenseStorage()
            storage.save_license({"key": "test"})
            storage.delete_license()
            assert storage.load_license() is None

    def test_usage_counter(self, tmp_path):
        with patch("src.licensing.storage.VOXTOOL_DIR", tmp_path), \
             patch("src.licensing.storage.USAGE_FILE", tmp_path / "usage.json"):
            from src.licensing.storage import LicenseStorage

            assert LicenseStorage.get_usage() == 0
            LicenseStorage.increment_usage()
            assert LicenseStorage.get_usage() == 1
            LicenseStorage.increment_usage()
            assert LicenseStorage.get_usage() == 2


class TestLicenseValidator:
    """Tests LicenseValidator."""

    def test_can_transcribe_under_limit(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator(free_limit=10)
        validator.storage = MagicMock()
        validator.storage.get_usage.return_value = 5
        validator.storage.load_license.return_value = None

        assert validator.can_transcribe() is True

    def test_cannot_transcribe_over_limit(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator(free_limit=10)
        validator.storage = MagicMock()
        validator.storage.get_usage.return_value = 10
        validator.storage.load_license.return_value = None

        assert validator.can_transcribe() is False

    def test_licensed_user_always_can_transcribe(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator(free_limit=10)
        validator.storage = MagicMock()
        validator.storage.get_usage.return_value = 99999
        validator.storage.load_license.return_value = {"license_key": "valid-key"}
        validator.client = MagicMock()
        validator.client.validate_license.return_value = {"valid": True}

        assert validator.can_transcribe() is True

    def test_increment_usage_returns_false_at_limit(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator(free_limit=5)
        validator.storage = MagicMock()
        validator.storage.load_license.return_value = None
        validator.storage.increment_usage.return_value = 6
        validator.storage.get_usage.return_value = 6

        # No license, count exceeds limit
        assert validator.increment_usage() is False

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

    def test_get_usage_info(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator(free_limit=1000)
        validator.storage = MagicMock()
        validator.storage.load_license.return_value = None
        validator.storage.get_usage.return_value = 42

        info = validator.get_usage_info()
        assert info["licensed"] is False
        assert info["usage"] == 42
        assert info["limit"] == 1000
        assert info["remaining"] == 958

    def test_offline_validation_trusts_cache(self):
        from src.licensing.validator import LicenseValidator

        validator = LicenseValidator()
        validator.storage = MagicMock()
        validator.storage.load_license.return_value = {"license_key": "key-123"}
        validator.client = MagicMock()
        validator.client.validate_license.side_effect = LicenseError("Network error")

        # Should trust local cache when offline
        assert validator.is_licensed() is True
