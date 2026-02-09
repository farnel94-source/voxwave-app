"""Validation de licence : cache local + API LemonSqueezy."""

import logging
import time
from typing import Optional

from src.licensing.lemonsqueezy import LemonSqueezyClient
from src.licensing.storage import LicenseStorage
from src.utils.exceptions import LicenseError

logger = logging.getLogger(__name__)


class LicenseValidator:
    """Vérifie la licence (cache local + API) et gère le free tier."""

    def __init__(self, free_limit: int = 1000, cache_duration: int = 86400) -> None:
        """Initialise le validateur de licence.

        Args:
            free_limit: Nombre max de transcriptions gratuites.
            cache_duration: Durée du cache en secondes (24h par défaut).
        """
        self.free_limit = free_limit
        self.cache_duration = cache_duration
        self.storage = LicenseStorage()
        self.client = LemonSqueezyClient()
        self._cached_valid: Optional[bool] = None
        self._cache_time: float = 0.0

    def is_licensed(self) -> bool:
        """Vérifie si une licence valide existe.

        Returns:
            True si licence valide (cache ou API).
        """
        # Cache local
        if self._cached_valid is not None:
            if time.time() - self._cache_time < self.cache_duration:
                return self._cached_valid

        license_data = self.storage.load_license()
        if not license_data:
            return False

        # Valider via API (avec fallback sur le cache local)
        try:
            result = self.client.validate_license(license_data["license_key"])
            self._cached_valid = result.get("valid", False)
            self._cache_time = time.time()
            return self._cached_valid
        except LicenseError:
            # Offline : faire confiance au cache local
            logger.warning("Validation licence offline, utilisation du cache local")
            self._cached_valid = True
            self._cache_time = time.time()
            return True

    def can_transcribe(self) -> bool:
        """Vérifie si l'utilisateur peut encore transcrire.

        Returns:
            True si licence valide OU free tier pas épuisé.
        """
        if self.is_licensed():
            return True

        usage = self.storage.get_usage()
        if usage >= self.free_limit:
            logger.warning(
                f"Free tier épuisé ({usage}/{self.free_limit}). "
                "Activez une licence pour continuer."
            )
            return False
        return True

    def increment_usage(self) -> bool:
        """Incrémente le compteur et vérifie la limite.

        Returns:
            True si l'utilisation est autorisée, False si limite atteinte.
        """
        if self.is_licensed():
            return True

        count = self.storage.increment_usage()
        remaining = self.free_limit - count
        if remaining <= 0:
            return False
        if remaining <= 50:
            logger.info(f"Free tier: {remaining} transcriptions restantes")
        return True

    def activate_license(self, license_key: str) -> bool:
        """Active une licence via l'API et la sauvegarde localement.

        Args:
            license_key: Clé de licence à activer.

        Returns:
            True si activation réussie.

        Raises:
            LicenseError: Si l'activation échoue.
        """
        result = self.client.activate_license(license_key)
        license_data = {
            "license_key": license_key,
            "instance_id": result.get("instance", {}).get("id", ""),
            "activated_at": time.time(),
        }
        self.storage.save_license(license_data)
        self._cached_valid = True
        self._cache_time = time.time()
        logger.info("Licence activée avec succès")
        return True

    def get_usage_info(self) -> dict:
        """Retourne les infos d'utilisation.

        Returns:
            Dict avec licensed, usage, limit, remaining.
        """
        licensed = self.is_licensed()
        usage = self.storage.get_usage()
        return {
            "licensed": licensed,
            "usage": usage,
            "limit": self.free_limit if not licensed else None,
            "remaining": max(0, self.free_limit - usage) if not licensed else None,
        }
