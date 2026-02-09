"""Stockage local chiffré de la licence et compteur d'utilisation."""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

VOXTOOL_DIR = Path.home() / ".voxtool"
LICENSE_FILE = VOXTOOL_DIR / "license.enc"
USAGE_FILE = VOXTOOL_DIR / "usage.json"
KEY_FILE = VOXTOOL_DIR / ".key"


class LicenseStorage:
    """Sauvegarde et lecture de la licence locale chiffrée."""

    def __init__(self) -> None:
        VOXTOOL_DIR.mkdir(parents=True, exist_ok=True)
        self._fernet = self._get_or_create_fernet()

    def _get_or_create_fernet(self) -> Fernet:
        """Charge ou génère la clé de chiffrement locale.

        Returns:
            Instance Fernet pour chiffrement/déchiffrement.
        """
        if KEY_FILE.exists():
            key = KEY_FILE.read_bytes()
        else:
            key = Fernet.generate_key()
            KEY_FILE.write_bytes(key)
            # Restreindre les permissions sur la clé
            try:
                os.chmod(KEY_FILE, 0o600)
            except OSError:
                pass  # Windows ne supporte pas chmod de la même façon
        return Fernet(key)

    def save_license(self, license_data: dict) -> None:
        """Sauvegarde les données de licence chiffrées.

        Args:
            license_data: Dict contenant license_key, instance_id, etc.
        """
        encrypted = self._fernet.encrypt(json.dumps(license_data).encode())
        LICENSE_FILE.write_bytes(encrypted)
        logger.info("Licence sauvegardée localement")

    def load_license(self) -> Optional[dict]:
        """Charge les données de licence.

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
            logger.info("Licence locale supprimée")

    @staticmethod
    def get_usage() -> int:
        """Retourne le compteur d'utilisation actuel.

        Returns:
            Nombre de transcriptions effectuées.
        """
        if not USAGE_FILE.exists():
            return 0
        try:
            data = json.loads(USAGE_FILE.read_text())
            return data.get("count", 0)
        except (json.JSONDecodeError, OSError):
            return 0

    @staticmethod
    def increment_usage() -> int:
        """Incrémente et retourne le compteur d'utilisation.

        Returns:
            Nouveau compteur.
        """
        VOXTOOL_DIR.mkdir(parents=True, exist_ok=True)
        count = LicenseStorage.get_usage() + 1
        USAGE_FILE.write_text(json.dumps({"count": count}))
        return count
