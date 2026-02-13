"""Stockage local chiffre de la licence et compteur d'utilisation."""

import json
import logging
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

VOXTOOL_DIR = Path.home() / ".voxtool"
LICENSE_FILE = VOXTOOL_DIR / "license.enc"
USAGE_FILE = VOXTOOL_DIR / "usage.json"
KEY_FILE = VOXTOOL_DIR / ".key"


class LicenseStorage:
    """Sauvegarde et lecture de la licence locale chiffree."""

    def __init__(self) -> None:
        VOXTOOL_DIR.mkdir(parents=True, exist_ok=True)
        self._fernet = self._get_or_create_fernet()

    def _get_or_create_fernet(self) -> Fernet:
        """Charge ou genere la cle de chiffrement locale.

        Returns:
            Instance Fernet pour chiffrement/dechiffrement.
        """
        if KEY_FILE.exists():
            key = KEY_FILE.read_bytes()
        else:
            key = Fernet.generate_key()
            KEY_FILE.write_bytes(key)
            try:
                os.chmod(KEY_FILE, 0o600)
            except OSError:
                pass
        return Fernet(key)

    def save_license(self, license_data: dict) -> None:
        """Sauvegarde les donnees de licence chiffrees.

        Args:
            license_data: Dict contenant license_key, instance_id, etc.
        """
        encrypted = self._fernet.encrypt(json.dumps(license_data).encode())
        LICENSE_FILE.write_bytes(encrypted)
        logger.info("Licence sauvegardee localement")

    def load_license(self) -> Optional[dict]:
        """Charge les donnees de licence.

        Returns:
            Dict licence ou None si pas de licence.
        """
        if not LICENSE_FILE.exists():
            return None
        try:
            encrypted = LICENSE_FILE.read_bytes()
            decrypted = self._fernet.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.warning(f"Impossible de lire la licence locale: {e}")
            return None

    def delete_license(self) -> None:
        """Supprime la licence locale."""
        if LICENSE_FILE.exists():
            LICENSE_FILE.unlink()
            logger.info("Licence locale supprimee")

    @staticmethod
    def _load_usage_data() -> dict:
        """Charge les donnees d'utilisation brutes.

        Returns:
            Dict avec 'count', 'daily_count', 'daily_date'.
        """
        if not USAGE_FILE.exists():
            return {"count": 0, "daily_count": 0, "daily_date": ""}
        try:
            data = json.loads(USAGE_FILE.read_text())
            return {
                "count": data.get("count", 0),
                "daily_count": data.get("daily_count", 0),
                "daily_date": data.get("daily_date", ""),
            }
        except (json.JSONDecodeError, OSError):
            return {"count": 0, "daily_count": 0, "daily_date": ""}

    @staticmethod
    def _save_usage_data(data: dict) -> None:
        """Sauvegarde les donnees d'utilisation (ecriture atomique).

        Args:
            data: Dict avec count, daily_count, daily_date.
        """
        VOXTOOL_DIR.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(dir=VOXTOOL_DIR, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(data, f)
            os.replace(tmp_path, USAGE_FILE)
        except OSError as e:
            logger.error(f"Erreur ecriture compteur: {e}")
            USAGE_FILE.write_text(json.dumps(data))

    @staticmethod
    def get_usage() -> int:
        """Retourne le compteur d'utilisation total.

        Returns:
            Nombre de transcriptions effectuees (total).
        """
        data = LicenseStorage._load_usage_data()
        return data["count"]

    @staticmethod
    def get_daily_usage() -> int:
        """Retourne le compteur d'utilisation du jour.

        Reset automatiquement si le jour a change.

        Returns:
            Nombre de transcriptions effectuees aujourd'hui.
        """
        data = LicenseStorage._load_usage_data()
        today = date.today().isoformat()
        if data["daily_date"] != today:
            return 0
        return data["daily_count"]

    @staticmethod
    def increment_usage() -> int:
        """Incremente les compteurs (total + journalier).

        Reset le compteur journalier si le jour a change.

        Returns:
            Nouveau compteur total.
        """
        data = LicenseStorage._load_usage_data()
        today = date.today().isoformat()

        # Reset journalier si nouveau jour
        if data["daily_date"] != today:
            data["daily_count"] = 0
            data["daily_date"] = today

        data["count"] += 1
        data["daily_count"] += 1

        LicenseStorage._save_usage_data(data)
        return data["count"]
