"""Tests pour src/config/validator.py et src/config/defaults.py."""

import pytest

from src.config.defaults import DEFAULT_CONFIG
from src.config.validator import ConfigValidator, deep_merge


class TestDeepMerge:
    """Tests du merge récursif."""

    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 100}}
        result = deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 99, "z": 100}, "b": 3}

    def test_override_dict_with_scalar(self):
        base = {"a": {"x": 1}}
        override = {"a": "flat"}
        result = deep_merge(base, override)
        assert result == {"a": "flat"}

    def test_empty_override(self):
        base = {"a": 1}
        result = deep_merge(base, {})
        assert result == {"a": 1}

    def test_empty_base(self):
        override = {"a": 1}
        result = deep_merge({}, override)
        assert result == {"a": 1}


class TestConfigValidator:
    """Tests de validation de la config."""

    def test_full_merge_with_defaults(self):
        config = ConfigValidator.validate_and_merge({})
        assert config["hotkey"] == "F8"
        assert config["audio"]["sample_rate"] == 16000
        assert config["audio"]["feedback"]["enabled"] is True
        assert config["cleaning"]["mode"] == "verbatim"

    def test_user_override_preserved(self):
        config = ConfigValidator.validate_and_merge({"hotkey": "F9"})
        assert config["hotkey"] == "F9"

    def test_invalid_hotkey_falls_back(self):
        config = ConfigValidator.validate_and_merge({"hotkey": "SPACE"})
        assert config["hotkey"] == "F8"

    def test_invalid_injection_mode_falls_back(self):
        config = ConfigValidator.validate_and_merge({"injection": "shout"})
        assert config["injection"] == "paste"

    def test_invalid_sample_rate_falls_back(self):
        config = ConfigValidator.validate_and_merge({"audio": {"sample_rate": 100}})
        assert config["audio"]["sample_rate"] == 16000

    def test_invalid_transcription_provider_falls_back(self):
        config = ConfigValidator.validate_and_merge(
            {"transcription": {"provider": "magic"}}
        )
        assert config["transcription"]["provider"] == "hybrid"

    def test_invalid_cleaning_mode_falls_back(self):
        config = ConfigValidator.validate_and_merge(
            {"cleaning": {"mode": "ultra"}}
        )
        assert config["cleaning"]["mode"] == "verbatim"

    def test_invalid_feedback_volume_falls_back(self):
        config = ConfigValidator.validate_and_merge(
            {"audio": {"feedback": {"volume": 5.0}}}
        )
        assert config["audio"]["feedback"]["volume"] == 0.5

    def test_partial_config_merged(self):
        config = ConfigValidator.validate_and_merge(
            {"whisper": {"model": "large-v3"}}
        )
        assert config["whisper"]["model"] == "large-v3"
        assert config["whisper"]["beam_size"] == 5  # Défaut préservé


class TestDefaultConfig:
    """Tests que DEFAULT_CONFIG a les clés attendues."""

    def test_has_all_sections(self):
        assert "hotkey" in DEFAULT_CONFIG
        assert "audio" in DEFAULT_CONFIG
        assert "transcription" in DEFAULT_CONFIG
        assert "whisper" in DEFAULT_CONFIG
        assert "groq" in DEFAULT_CONFIG
        assert "cleaning" in DEFAULT_CONFIG
        assert "licensing" in DEFAULT_CONFIG

    def test_audio_has_feedback(self):
        assert "feedback" in DEFAULT_CONFIG["audio"]
        assert "enabled" in DEFAULT_CONFIG["audio"]["feedback"]
        assert "volume" in DEFAULT_CONFIG["audio"]["feedback"]
