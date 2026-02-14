"""Tests d'intégration pour src/app.py."""

from unittest.mock import patch, MagicMock, PropertyMock

import numpy as np
import pytest

from src.app import VoxTool, load_config
from src.transcription.hallucinations import is_hallucination


class TestLoadConfig:
    """Tests load_config."""

    def test_load_valid_config(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("hotkey: F9\nlanguage: en\n")
        config = load_config(str(config_file))
        assert config["hotkey"] == "F9"
        # Defaults should be merged
        assert "audio" in config

    def test_load_missing_config_uses_defaults(self):
        config = load_config("nonexistent_file_xyz.yaml")
        assert config["hotkey"] == "F8"
        assert config["audio"]["sample_rate"] == 16000

    def test_load_empty_config_uses_defaults(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        config = load_config(str(config_file))
        assert config["hotkey"] == "F8"


class TestVoxToolHallucination:
    """Tests detection d'hallucinations (delegue a hallucinations.py)."""

    @pytest.mark.parametrize("text", [
        "merci.", "Merci !", "merci",
        "sous-titrage", "Sous-titres",
        "...", "\u2026",
        "bye", "thank you",
    ])
    def test_known_hallucinations(self, text):
        assert is_hallucination(text) is True

    @pytest.mark.parametrize("text", [
        "oui", "non", "ok", "bien", "voil\u00e0",
    ])
    def test_generic_short_hallucinations(self, text):
        assert is_hallucination(text) is True

    @pytest.mark.parametrize("text", [
        "Je vais faire un git push sur la branche main.",
        "Bonjour, comment \u00e7a va aujourd'hui ?",
        "Il faut que je finisse ce projet.",
    ])
    def test_valid_text_not_hallucination(self, text):
        assert is_hallucination(text) is False


class TestVoxToolPipeline:
    """Tests pipeline complet avec mocks."""

    def _create_app(self, config):
        app = VoxTool(config)
        app.feedback = MagicMock()
        app.listener = MagicMock()
        app.processor = MagicMock()
        app.engine = MagicMock()
        app.pipeline = MagicMock()
        app.injector = MagicMock()
        app.tray = MagicMock()
        app.license_validator = MagicMock()
        app.license_validator.increment_usage.return_value = True
        return app

    def test_process_audio_success(self, sample_config, sample_audio):
        app = self._create_app(sample_config)
        app.processor.prepare_for_whisper.return_value = sample_audio
        app.engine.transcribe.return_value = "Bonjour le monde"
        app.pipeline.clean.return_value = "Bonjour le monde."

        app._process_audio(sample_audio)

        app.engine.transcribe.assert_called_once()
        app.pipeline.clean.assert_called_once_with("Bonjour le monde")
        app.injector.inject.assert_called_once_with("Bonjour le monde.")
        app.feedback.play_complete.assert_called_once()

    def test_process_audio_too_short(self, sample_config):
        app = self._create_app(sample_config)
        short = np.zeros(100, dtype=np.float32)  # Way too short
        app._process_audio(short)
        app.engine.transcribe.assert_not_called()

    def test_process_audio_empty_transcription(self, sample_config, sample_audio):
        app = self._create_app(sample_config)
        app.processor.prepare_for_whisper.return_value = sample_audio
        app.engine.transcribe.return_value = ""

        app._process_audio(sample_audio)
        app.pipeline.clean.assert_not_called()

    def test_process_audio_hallucination_filtered(self, sample_config, sample_audio):
        app = self._create_app(sample_config)
        app.processor.prepare_for_whisper.return_value = sample_audio
        app.engine.transcribe.return_value = "Merci."

        app._process_audio(sample_audio)
        app.pipeline.clean.assert_not_called()

    def test_process_audio_error_plays_error_sound(self, sample_config, sample_audio):
        app = self._create_app(sample_config)
        app.processor.prepare_for_whisper.return_value = sample_audio
        app.engine.transcribe.side_effect = RuntimeError("boom")

        app._process_audio(sample_audio)
        app.feedback.play_error.assert_called_once()

    def test_process_audio_license_blocked(self, sample_config, sample_audio):
        app = self._create_app(sample_config)
        app.license_validator.increment_usage.return_value = False

        app._process_audio(sample_audio)
        app.engine.transcribe.assert_not_called()
        app.tray.show_notification.assert_called_once()

    def test_on_start_plays_feedback(self, sample_config):
        app = self._create_app(sample_config)
        app.capture = MagicMock()
        app._on_start()
        app.feedback.play_start.assert_called_once()
        app.tray.set_state.assert_called_with("recording")
        app.capture.start.assert_called_once()

    def test_on_stop_plays_feedback(self, sample_config):
        app = self._create_app(sample_config)
        app.capture = MagicMock()
        app.capture.get_buffer.return_value = np.array([], dtype=np.float32)
        app._on_stop()
        # play_stop is now submitted to executor, just check it was called via executor
        app.tray.set_state.assert_called_with("processing")

    def test_process_audio_chunked(self, sample_config):
        """Test chunked processing for long audio."""
        sample_config["audio"]["chunking_threshold"] = 5.0
        app = self._create_app(sample_config)
        # 10s audio at 16kHz
        long_audio = np.random.randn(160000).astype(np.float32) * 0.5
        app.processor.prepare_for_whisper.return_value = long_audio
        app.processor.split_at_silence.return_value = [
            long_audio[:80000], long_audio[80000:]
        ]
        app.engine.transcribe.side_effect = ["Premiere partie", "Deuxieme partie"]
        app.pipeline.clean.side_effect = ["Premiere partie.", "Deuxieme partie."]
        app.waveform = MagicMock()

        app._process_audio(long_audio)

        assert app.engine.transcribe.call_count == 2
        app.injector.inject.assert_called_once()
        injected = app.injector.inject.call_args[0][0]
        assert "Premiere partie" in injected
        assert "Deuxieme partie" in injected

    def test_prewarm_engines(self, sample_config):
        """Test that prewarm submits tasks to executor."""
        app = self._create_app(sample_config)
        app.engine = MagicMock()
        app.engine.preload = MagicMock()
        app.pipeline = MagicMock()
        app.pipeline._local_cleaner = MagicMock()
        app.pipeline._local_cleaner.is_available.return_value = True

        app._prewarm_engines()

        # Executor should have submitted tasks (non-blocking)
        app._executor.shutdown(wait=True)

    def test_transcribe_and_clean_returns_text(self, sample_config, sample_audio):
        app = self._create_app(sample_config)
        app.processor.prepare_for_whisper.return_value = sample_audio
        app.engine.transcribe.return_value = "Bonjour le monde"
        app.pipeline.clean.return_value = "Bonjour le monde."
        app.waveform = MagicMock()

        result = app._transcribe_and_clean(sample_audio)
        assert result == "Bonjour le monde."

    def test_transcribe_and_clean_returns_none_for_hallucination(self, sample_config, sample_audio):
        app = self._create_app(sample_config)
        app.engine.transcribe.return_value = "Merci."
        app.waveform = MagicMock()

        result = app._transcribe_and_clean(sample_audio)
        assert result is None
