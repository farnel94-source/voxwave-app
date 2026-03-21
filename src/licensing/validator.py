"""Validation de licence : cache local + API LemonSqueezy.

Free tier : transcription locale + regex uniquement, limite journaliere.
Paid tier : transcription cloud + nettoyage IA, illimite.
"""

import logging
import os
from pathlib import Path
import time
from typing import Optional

from src.licensing.lemonsqueezy import LemonSqueezyClient
from src.licensing.storage import LicenseStorage
from src.utils.exceptions import LicenseError

logger = logging.getLogger(__name__)


def _is_dev_mode() -> bool:
    """Verifie si le mode developpeur est active.

    Le dev mode est active par la presence du fichier ~/.voxwave/.dev
    (pas par variable d'env, pour eviter toute exploitation).

    Returns:
        True si le fichier ~/.voxwave/.dev existe.
    """
    dev_file = Path.home() / ".voxwave" / ".dev"
    return dev_file.is_file()


class LicenseValidator:
    """Verifie la licence (cache local + API) et gere le free tier."""

    def __init__(
        self,
        free_daily_limit: int = 200,
        free_limit: int = 1000,
        cache_duration: int = 86400,
    ) -> None:
        """Initialise le validateur de licence.

        Args:
            free_daily_limit: Nombre max de transcriptions gratuites par jour.
            free_limit: Nombre max de transcriptions gratuites (total, legacy).
            cache_duration: Duree du cache en secondes (24h par defaut).
        """
        self.free_daily_limit = free_daily_limit
        self.free_limit = free_limit
        self.cache_duration = cache_duration
        self.storage = LicenseStorage()
        self.client = LemonSqueezyClient()
        self._cached_valid: Optional[bool] = None
        self._cache_time: float = 0.0

    def is_licensed(self) -> bool:
        """Verifie si une licence valide existe.

        Returns:
            True si licence valide (cache ou API) ou mode dev.
        """
        if _is_dev_mode():
            return True

        # Cache local
        if self._cached_valid is not None:
            if time.time() - self._cache_time < self.cache_duration:
                return self._cached_valid

        license_data = self.storage.load_license()
        if not license_data:
            return False

        # Valider via API (avec fallback sur le cache local)
        license_key = license_data.get("license_key")
        if not license_key:
            return False

        try:
            result = self.client.validate_license(license_key)
            self._cached_valid = result.get("valid", False)
            self._cache_time = time.time()
            return self._cached_valid
        except LicenseError:
            # Offline : faire confiance au cache SEULEMENT si < 7 jours
            max_offline_seconds = 7 * 86400
            if (
                self._cached_valid is not None
                and (time.time() - self._cache_time) < max_offline_seconds
            ):
                logger.warning(
                    "Validation licence offline, utilisation du cache local "
                    "(age: %.1f jours)",
                    (time.time() - self._cache_time) / 86400,
                )
                return self._cached_valid
            logger.warning(
                "Validation licence offline et cache expire (>7 jours) "
                "— retour au free tier"
            )
            self._cached_valid = False
            self._cache_time = 0.0
            return False

    def can_transcribe(self) -> bool:
        """Verifie si l'utilisateur peut encore transcrire.

        Returns:
            True si licence valide OU free tier pas epuise.
        """
        if self.is_licensed():
            return True

        daily_usage = self.storage.get_daily_usage()
        if daily_usage >= self.free_daily_limit:
            logger.warning(
                f"Free tier journalier epuise ({daily_usage}/{self.free_daily_limit}). "
                "Activez une licence pour continuer."
            )
            return False
        return True

    def increment_usage(self) -> bool:
        """Verifie la limite PUIS incremente le compteur.

        Returns:
            True si l'utilisation est autorisee, False si limite atteinte.
        """
        return self.increment_usage_for_provider("cloud")

    def increment_usage_for_provider(self, provider: str = "cloud") -> bool:
        """Verifie la limite PUIS incremente le compteur.

        Le local (Whisper + regex) n'est jamais bloque.
        Seul le cloud (Groq + OpenAI) est soumis a la limite free tier.

        Args:
            provider: 'local' ou 'cloud'/'hybrid'.

        Returns:
            True si l'utilisation est autorisee, False si limite atteinte.
        """
        if self.is_licensed():
            return True

        # Le local est toujours autorise, meme apres la limite
        if provider == "local":
            return True

        # Verifier la limite journaliere AVANT d'incrementer
        daily_usage = self.storage.get_daily_usage()
        if daily_usage >= self.free_daily_limit:
            return False

        self.storage.increment_usage()
        remaining = self.free_daily_limit - daily_usage - 1
        if remaining <= 10:
            logger.info(f"Free tier: {remaining} transcriptions restantes aujourd'hui")
        return True

    def get_transcription_provider(self) -> str:
        """Retourne le provider de transcription autorise.

        Returns:
            'hybrid' pour paid tier, 'local' pour free tier.
        """
        if self.is_licensed():
            return "hybrid"
        return "local"

    def get_cleaning_provider(self) -> str:
        """Retourne le provider de nettoyage autorise.

        Returns:
            'hybrid' pour paid tier, 'local' (regex) pour free tier.
        """
        if self.is_licensed():
            return "hybrid"
        return "local"

    def activate_license(self, license_key: str) -> bool:
        """Active une licence via l'API et la sauvegarde localement.

        Args:
            license_key: Cle de licence a activer.

        Returns:
            True si activation reussie.

        Raises:
            LicenseError: Si l'activation echoue.
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
        logger.info("Licence activee avec succes")
        return True

    def get_usage_info(self) -> dict:
        """Retourne les infos d'utilisation.

        Returns:
            Dict avec licensed, usage, daily_usage, daily_limit, remaining_today.
        """
        licensed = self.is_licensed()
        usage = self.storage.get_usage()
        daily_usage = self.storage.get_daily_usage()
        return {
            "licensed": licensed,
            "usage": usage,
            "daily_usage": daily_usage,
            "daily_limit": self.free_daily_limit if not licensed else None,
            "remaining_today": max(0, self.free_daily_limit - daily_usage) if not licensed else None,
        }

    def days_remaining(self) -> Optional[int]:
        """Retourne le nombre de jours restants sur la licence.

        Returns:
            Nombre de jours ou None si pas de licence / lifetime.
        """
        license_data = self.storage.load_license()
        if not license_data:
            return None
        # Lifetime licenses n'ont pas d'expiration
        expires_at = license_data.get("expires_at")
        if not expires_at:
            return None
        remaining = int(expires_at - time.time()) // 86400
        return max(0, remaining)
