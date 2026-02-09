"""Validation et merge de la configuration utilisateur avec les valeurs par défaut."""

import logging
from typing import Any

from src.config.defaults import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


def deep_merge(base: dict, override: dict) -> dict:
    """Merge récursif de deux dicts. override écrase base.

    Args:
        base: Dict de base (défauts).
        override: Dict utilisateur (prioritaire).

    Returns:
        Dict fusionné.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigValidator:
    """Valide et complète la configuration utilisateur."""

    VALID_PROVIDERS = ("hybrid", "cloud", "local")
    VALID_CLEANING_MODES = ("verbatim", "quality")
    VALID_HOTKEYS = ("F8", "F9", "F10", "F11", "F12")
    VALID_INJECTION_MODES = ("paste", "type")

    @classmethod
    def validate_and_merge(cls, user_config: dict) -> dict:
        """Fusionne la config utilisateur avec les défauts et valide.

        Args:
            user_config: Configuration chargée depuis config.yaml.

        Returns:
            Configuration complète et validée.
        """
        config = deep_merge(DEFAULT_CONFIG, user_config)
        cls._validate(config)
        return config

    @classmethod
    def _validate(cls, config: dict) -> None:
        """Valide les valeurs de la configuration.

        Args:
            config: Configuration complète.

        Raises:
            ValueError: Si une valeur est invalide.
        """
        # Hotkey
        if config.get("hotkey") not in cls.VALID_HOTKEYS:
            logger.warning(
                f"Hotkey '{config.get('hotkey')}' invalide, utilisation de F8"
            )
            config["hotkey"] = "F8"

        # Injection mode
        if config.get("injection") not in cls.VALID_INJECTION_MODES:
            logger.warning(
                f"Mode injection '{config.get('injection')}' invalide, utilisation de paste"
            )
            config["injection"] = "paste"

        # Audio
        audio = config.get("audio", {})
        if not (8000 <= audio.get("sample_rate", 16000) <= 48000):
            logger.warning("sample_rate invalide, utilisation de 16000")
            config["audio"]["sample_rate"] = 16000

        # Transcription provider
        trans_provider = config.get("transcription", {}).get("provider", "hybrid")
        if trans_provider not in cls.VALID_PROVIDERS:
            logger.warning(
                f"Transcription provider '{trans_provider}' invalide, utilisation de hybrid"
            )
            config["transcription"]["provider"] = "hybrid"

        # Cleaning
        cleaning = config.get("cleaning", {})
        if cleaning.get("mode") not in cls.VALID_CLEANING_MODES:
            logger.warning(
                f"Cleaning mode '{cleaning.get('mode')}' invalide, utilisation de verbatim"
            )
            config["cleaning"]["mode"] = "verbatim"

        if cleaning.get("provider") not in cls.VALID_PROVIDERS:
            logger.warning(
                f"Cleaning provider '{cleaning.get('provider')}' invalide, utilisation de hybrid"
            )
            config["cleaning"]["provider"] = "hybrid"

        # Feedback volume
        feedback = audio.get("feedback", {})
        volume = feedback.get("volume", 0.5)
        if not (0.0 <= volume <= 1.0):
            logger.warning(f"Volume feedback {volume} invalide, utilisation de 0.5")
            config["audio"]["feedback"]["volume"] = 0.5
