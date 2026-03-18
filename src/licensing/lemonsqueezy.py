"""Client HTTP pour l'API LemonSqueezy."""

import logging
from typing import Optional

import requests

from src.utils.exceptions import LicenseError

logger = logging.getLogger(__name__)

LEMON_API_URL = "https://api.lemonsqueezy.com/v1/licenses"


class LemonSqueezyClient:
    """Client pour valider et activer les licences LemonSqueezy."""

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    def validate_license(self, license_key: str) -> dict:
        """Valide une clé de licence via l'API.

        Args:
            license_key: Clé de licence à valider.

        Returns:
            Dict avec valid (bool), license_key (dict), meta, etc.

        Raises:
            LicenseError: Si l'appel API échoue.
        """
        try:
            response = requests.post(
                f"{LEMON_API_URL}/validate",
                json={"license_key": license_key},
                timeout=self.timeout,
            )
            data = response.json()
            if not data.get("valid", False):
                raise LicenseError(f"Licence invalide: {data.get('error', 'unknown')}")
            return data
        except requests.RequestException as e:
            raise LicenseError(f"Erreur API LemonSqueezy: {e}") from e

    def activate_license(self, license_key: str, instance_name: str = "VoxWave") -> dict:
        """Active une licence pour cette instance.

        Args:
            license_key: Clé de licence.
            instance_name: Nom de l'instance à activer.

        Returns:
            Dict de réponse API.

        Raises:
            LicenseError: Si l'activation échoue.
        """
        try:
            response = requests.post(
                f"{LEMON_API_URL}/activate",
                json={
                    "license_key": license_key,
                    "instance_name": instance_name,
                },
                timeout=self.timeout,
            )
            data = response.json()
            if not data.get("activated", False):
                raise LicenseError(f"Activation échouée: {data.get('error', 'unknown')}")
            return data
        except requests.RequestException as e:
            raise LicenseError(f"Erreur API LemonSqueezy: {e}") from e

    def deactivate_license(self, license_key: str, instance_id: str) -> dict:
        """Désactive une licence.

        Args:
            license_key: Clé de licence.
            instance_id: ID de l'instance à désactiver.

        Returns:
            Dict de réponse API.

        Raises:
            LicenseError: Si la désactivation échoue.
        """
        try:
            response = requests.post(
                f"{LEMON_API_URL}/deactivate",
                json={
                    "license_key": license_key,
                    "instance_id": instance_id,
                },
                timeout=self.timeout,
            )
            return response.json()
        except requests.RequestException as e:
            raise LicenseError(f"Erreur API LemonSqueezy: {e}") from e
