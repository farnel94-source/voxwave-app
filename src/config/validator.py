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


def _validate_hotkey(hotkey_str: str) -> bool:
    """Valide un format hotkey (combo ou touche simple).

    Args:
        hotkey_str: Chaine hotkey (ex: "F8", "Ctrl+Shift+V").

    Returns:
        True si le format est valide.
    """
    try:
        from src.hotkey.listener import parse_hotkey
        parse_hotkey(hotkey_str)
        return True
    except (ValueError, Exception):
        return False


class ConfigValidator:
    """Valide et complète la configuration utilisateur."""

    VALID_PROVIDERS = ("hybrid", "cloud", "local", "proxy")
    VALID_CLEANING_MODES = ("raw", "auto")
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
        if not _validate_hotkey(config.get("hotkey", "F8")):
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
        mode = cleaning.get("mode")
        if mode not in cls.VALID_CLEANING_MODES:
            # Migration depuis anciens modes
            if mode in ("verbatim", "quality"):
                logger.info(f"Migration cleaning mode '{mode}' → 'auto'")
                config["cleaning"]["mode"] = "auto"
            else:
                logger.warning(f"Cleaning mode '{mode}' invalide, utilisation de 'auto'")
                config["cleaning"]["mode"] = "auto"

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
