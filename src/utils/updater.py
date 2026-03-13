"""Vérification de mise à jour via GitHub Releases (public, sans token)."""

import json
import logging
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from packaging.version import Version

logger = logging.getLogger(__name__)

GITHUB_REPO = "OWNER/REPO"  # placeholder — remplacer par le vrai repo
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
REQUEST_TIMEOUT = (3, 5)  # (connect, read)
CACHE_TTL_HOURS = 12

# Réutilise le même dossier que licensing/storage.py
VOXWAVE_DIR = Path.home() / ".voxwave"
CACHE_FILE = VOXWAVE_DIR / "update_cache.json"


@dataclass
class UpdateInfo:
    """Informations sur une mise à jour disponible."""

    version: str
    download_url: str


def _get_platform_suffix() -> str:
    """Retourne le suffixe d'asset attendu pour la plateforme courante."""
    if sys.platform == "win32":
        return ".exe"
    return ".AppImage"


def _read_cache() -> Optional[dict]:
    """Lit le cache et retourne son contenu si encore valide (<TTL).

    Returns:
        Dict avec 'version', 'download_url', 'timestamp' ou None.
    """
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        age_hours = (time.time() - data.get("timestamp", 0)) / 3600
        if age_hours < CACHE_TTL_HOURS:
            return data
        return None
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def _write_cache(version: str, download_url: str) -> None:
    """Écrit le cache de manière atomique (tempfile + os.replace)."""
    VOXWAVE_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "version": version,
        "download_url": download_url,
        "timestamp": time.time(),
    }
    try:
        fd, tmp_path = tempfile.mkstemp(dir=VOXWAVE_DIR, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp_path, CACHE_FILE)
    except OSError as e:
        logger.debug(f"Erreur écriture cache update: {e}")


def _find_platform_asset(assets: list) -> Optional[str]:
    """Trouve l'URL de téléchargement pour la plateforme courante.

    Args:
        assets: Liste d'assets de la release GitHub.

    Returns:
        URL de téléchargement ou None.
    """
    suffix = _get_platform_suffix()
    for asset in assets:
        name = asset.get("name", "")
        if name.endswith(suffix):
            return asset.get("browser_download_url")
    return None


def check_for_update(current_version: str) -> Optional[UpdateInfo]:
    """Vérifie si une nouvelle version est disponible sur GitHub Releases.

    Utilise un cache local (12h TTL) pour limiter les appels API.
    Sur toute erreur (réseau, parsing, etc.) → retourne None sans crash.

    Args:
        current_version: Version courante (ex: "0.1.0").

    Returns:
        UpdateInfo si mise à jour disponible, None sinon.
    """
    try:
        # 1. Vérifier le cache
        cached = _read_cache()
        if cached:
            cached_version = cached.get("version", "")
            cached_url = cached.get("download_url", "")
            if cached_version and cached_url:
                if Version(cached_version) > Version(current_version):
                    return UpdateInfo(
                        version=cached_version, download_url=cached_url
                    )
                return None

        # 2. Appel API GitHub
        resp = requests.get(
            GITHUB_API_URL,
            timeout=REQUEST_TIMEOUT,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        resp.raise_for_status()
        data = resp.json()

        # 3. Extraire version (strip "v" prefix)
        tag = data.get("tag_name", "")
        remote_version = tag.lstrip("v")
        if not remote_version:
            return None

        # 4. Trouver l'asset pour la plateforme
        assets = data.get("assets", [])
        download_url = _find_platform_asset(assets)
        if not download_url:
            return None

        # 5. Sauvegarder dans le cache
        _write_cache(remote_version, download_url)

        # 6. Comparer les versions
        if Version(remote_version) > Version(current_version):
            return UpdateInfo(version=remote_version, download_url=download_url)

        return None

    except Exception as e:
        logger.debug(f"Check update échoué: {e}")
        return None
