"""Tests pour le module de vérification de mise à jour."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from src.utils.updater import (
    CACHE_TTL_HOURS,
    UpdateInfo,
    check_for_update,
)


def _make_github_response(
    tag: str = "v1.0.0",
    assets: list | None = None,
) -> dict:
    """Construit une réponse GitHub Releases simulée."""
    if assets is None:
        assets = [
            {
                "name": "VoxWave-1.0.0-Setup.exe",
                "browser_download_url": "https://github.com/OWNER/REPO/releases/download/v1.0.0/VoxWave-1.0.0-Setup.exe",
            },
            {
                "name": "VoxWave-1.0.0.AppImage",
                "browser_download_url": "https://github.com/OWNER/REPO/releases/download/v1.0.0/VoxWave-1.0.0.AppImage",
            },
        ]
    return {"tag_name": tag, "assets": assets}


@pytest.fixture(autouse=True)
def _no_cache(tmp_path, monkeypatch):
    """Redirige le cache vers un dossier temporaire pour chaque test."""
    monkeypatch.setattr("src.utils.updater.VOXWAVE_DIR", tmp_path)
    monkeypatch.setattr("src.utils.updater.CACHE_FILE", tmp_path / "update_cache.json")


class TestCheckForUpdate:
    """Tests pour check_for_update()."""

    @patch("src.utils.updater.requests.get")
    def test_new_version_available(self, mock_get):
        """Nouvelle version dispo → retourne UpdateInfo."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_github_response("v1.0.0")
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = check_for_update("0.1.0")

        assert result is not None
        assert isinstance(result, UpdateInfo)
        assert result.version == "1.0.0"
        assert "download" in result.download_url

    @patch("src.utils.updater.requests.get")
    def test_no_update_same_version(self, mock_get):
        """Même version → None."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_github_response("v0.1.0")
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = check_for_update("0.1.0")
        assert result is None

    @patch("src.utils.updater.requests.get")
    def test_network_error_returns_none(self, mock_get):
        """Erreur réseau → None (pas de crash)."""
        mock_get.side_effect = ConnectionError("No network")

        result = check_for_update("0.1.0")
        assert result is None

    @patch("src.utils.updater.requests.get")
    def test_timeout_returns_none(self, mock_get):
        """Timeout → None."""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        result = check_for_update("0.1.0")
        assert result is None

    @patch("src.utils.updater.requests.get")
    def test_cache_valid_no_api_call(self, mock_get, tmp_path):
        """Cache valide (<12h) → pas d'appel API."""
        cache_data = {
            "version": "2.0.0",
            "download_url": "https://example.com/VoxWave-2.0.0-Setup.exe",
            "timestamp": time.time(),  # maintenant = frais
        }
        cache_file = tmp_path / "update_cache.json"
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

        result = check_for_update("0.1.0")

        assert result is not None
        assert result.version == "2.0.0"
        mock_get.assert_not_called()

    @patch("src.utils.updater.requests.get")
    def test_cache_expired_calls_api(self, mock_get, tmp_path):
        """Cache expiré (>12h) → appel API."""
        cache_data = {
            "version": "2.0.0",
            "download_url": "https://example.com/VoxWave-2.0.0-Setup.exe",
            "timestamp": time.time() - (CACHE_TTL_HOURS + 1) * 3600,
        }
        cache_file = tmp_path / "update_cache.json"
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_github_response("v3.0.0")
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = check_for_update("0.1.0")

        assert result is not None
        assert result.version == "3.0.0"
        mock_get.assert_called_once()

    @patch("src.utils.updater.requests.get")
    def test_cache_corrupted_calls_api(self, mock_get, tmp_path):
        """Cache corrompu → check normal via API."""
        cache_file = tmp_path / "update_cache.json"
        cache_file.write_text("{invalid json", encoding="utf-8")

        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_github_response("v1.0.0")
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = check_for_update("0.1.0")

        assert result is not None
        assert result.version == "1.0.0"
        mock_get.assert_called_once()

    @patch("src.utils.updater.requests.get")
    def test_tag_with_v_prefix(self, mock_get):
        """Tag avec préfixe 'v' → comparaison correcte."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_github_response("v2.0.0")
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = check_for_update("1.0.0")

        assert result is not None
        assert result.version == "2.0.0"  # sans le "v"

    @patch("src.utils.updater.requests.get")
    def test_no_matching_asset_returns_none(self, mock_get):
        """Pas d'asset correspondant à la plateforme → None."""
        response = _make_github_response(
            "v2.0.0",
            assets=[
                {
                    "name": "VoxWave-2.0.0.dmg",
                    "browser_download_url": "https://example.com/VoxWave-2.0.0.dmg",
                }
            ],
        )
        mock_resp = MagicMock()
        mock_resp.json.return_value = response
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = check_for_update("0.1.0")
        assert result is None
