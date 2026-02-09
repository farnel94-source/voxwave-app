"""Tests pour src/licensing/lemonsqueezy.py."""

from unittest.mock import patch, MagicMock

import pytest

from src.licensing.lemonsqueezy import LemonSqueezyClient
from src.utils.exceptions import LicenseError


class TestLemonSqueezyClient:
    """Tests LemonSqueezyClient."""

    def test_init(self):
        client = LemonSqueezyClient(timeout=5)
        assert client.timeout == 5

    @patch("src.licensing.lemonsqueezy.requests.post")
    def test_validate_license_success(self, mock_post):
        mock_post.return_value.json.return_value = {"valid": True}
        client = LemonSqueezyClient()
        result = client.validate_license("key-123")
        assert result["valid"] is True

    @patch("src.licensing.lemonsqueezy.requests.post")
    def test_validate_license_invalid(self, mock_post):
        mock_post.return_value.json.return_value = {"valid": False, "error": "expired"}
        client = LemonSqueezyClient()
        with pytest.raises(LicenseError, match="invalide"):
            client.validate_license("bad-key")

    @patch("src.licensing.lemonsqueezy.requests.post")
    def test_validate_license_network_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.RequestException("Network error")
        client = LemonSqueezyClient()
        with pytest.raises(LicenseError, match="Erreur API"):
            client.validate_license("key-123")

    @patch("src.licensing.lemonsqueezy.requests.post")
    def test_activate_license_success(self, mock_post):
        mock_post.return_value.json.return_value = {
            "activated": True,
            "instance": {"id": "inst-1"},
        }
        client = LemonSqueezyClient()
        result = client.activate_license("key-123")
        assert result["activated"] is True

    @patch("src.licensing.lemonsqueezy.requests.post")
    def test_activate_license_failure(self, mock_post):
        mock_post.return_value.json.return_value = {"activated": False, "error": "limit"}
        client = LemonSqueezyClient()
        with pytest.raises(LicenseError, match="Activation"):
            client.activate_license("key-123")

    @patch("src.licensing.lemonsqueezy.requests.post")
    def test_deactivate_license(self, mock_post):
        mock_post.return_value.json.return_value = {"deactivated": True}
        client = LemonSqueezyClient()
        result = client.deactivate_license("key-123", "inst-1")
        assert result["deactivated"] is True

    @patch("src.licensing.lemonsqueezy.requests.post")
    def test_deactivate_license_network_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.RequestException("Offline")
        client = LemonSqueezyClient()
        with pytest.raises(LicenseError):
            client.deactivate_license("key-123", "inst-1")
