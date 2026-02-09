"""Tests supplémentaires pour app.py — initialization et helpers."""

from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from src.app import VoxTool, setup_logging


class TestSetupLogging:
    """Tests setup_logging."""

    def test_setup_logging_info(self):
        setup_logging("INFO")

    def test_setup_logging_debug(self):
        setup_logging("DEBUG")


class TestVoxToolInit:
    """Tests VoxTool init et helpers."""

    def test_init(self, sample_config):
        app = VoxTool(sample_config)
        assert app.config == sample_config
        assert app.capture is None
        assert app.tray is None

    def test_create_transcription_engine_local(self, sample_config):
        sample_config["whisper"]["language"] = "fr"
        app = VoxTool(sample_config)
        with patch("src.transcription.whisper_engine.WhisperEngine") as mock:
            engine = app._create_transcription_engine("local")
            mock.assert_called_once()

    @patch.dict("os.environ", {"GROQ_API_KEY": "test"})
    def test_create_transcription_engine_cloud(self, sample_config):
        app = VoxTool(sample_config)
        engine = app._create_transcription_engine("cloud")
        assert engine is not None

    @patch.dict("os.environ", {"GROQ_API_KEY": "test"})
    def test_create_transcription_engine_hybrid(self, sample_config):
        app = VoxTool(sample_config)
        engine = app._create_transcription_engine("hybrid")
        assert engine is not None

    def test_process_audio_truncates_long_audio(self, sample_config):
        app = VoxTool(sample_config)
        app.feedback = MagicMock()
        app.listener = MagicMock()
        app.processor = MagicMock()
        app.engine = MagicMock()
        app.pipeline = MagicMock()
        app.injector = MagicMock()
        app.tray = MagicMock()
        app.license_validator = MagicMock()
        app.license_validator.increment_usage.return_value = True

        # 130s audio (over max)
        long_audio = np.zeros(int(16000 * 130), dtype=np.float32)
        app.processor.prepare_for_whisper.return_value = long_audio[:int(16000 * 120)]
        app.engine.transcribe.return_value = "Texte long"
        app.pipeline.clean.return_value = "Texte long."

        app._process_audio(long_audio)
        # Should have been processed (not rejected)
        app.engine.transcribe.assert_called_once()

    def test_shutdown(self, sample_config):
        app = VoxTool(sample_config)
        app.listener = MagicMock()
        app.capture = MagicMock()
        app.capture.is_recording = True
        app._shutdown()
        app.listener.stop.assert_called_once()
        app.capture.stop.assert_called_once()

    def test_shutdown_no_recording(self, sample_config):
        app = VoxTool(sample_config)
        app.listener = MagicMock()
        app.capture = MagicMock()
        app.capture.is_recording = False
        app._shutdown()
        app.listener.stop.assert_called_once()
        app.capture.stop.assert_not_called()
