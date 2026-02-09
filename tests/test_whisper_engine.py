"""Tests pour src/transcription/whisper_engine.py (mocks du modèle)."""

from unittest.mock import patch, MagicMock
import sys

import numpy as np
import pytest

from src.transcription.whisper_engine import WhisperEngine


class TestWhisperEngine:
    """Tests WhisperEngine avec mocks."""

    def test_init(self):
        engine = WhisperEngine(model="base", language="fr")
        assert engine.model_name == "base"
        assert engine.language == "fr"

    def test_init_unsupported_model(self):
        with pytest.raises(ValueError, match="non supporté"):
            WhisperEngine(model="huge", language="fr")

    def test_supported_models(self):
        assert "tiny" in WhisperEngine.SUPPORTED_MODELS
        assert "base" in WhisperEngine.SUPPORTED_MODELS
        assert "large-v3" in WhisperEngine.SUPPORTED_MODELS

    def test_detect_compute_type_no_torch(self):
        engine = WhisperEngine(model="base")
        # Without CUDA, should default to int8
        assert engine.compute_type == "int8"

    def test_custom_compute_type(self):
        engine = WhisperEngine(model="base", compute_type="float16")
        assert engine.compute_type == "float16"

    @patch.dict(sys.modules, {"faster_whisper": MagicMock()})
    def test_load_model(self):
        engine = WhisperEngine(model="base", language="fr")
        engine._load_model()
        assert engine._model is not None

    @patch.dict(sys.modules, {"faster_whisper": MagicMock()})
    def test_transcribe(self):
        engine = WhisperEngine(model="base", language="fr")

        mock_segment = MagicMock()
        mock_segment.text = "Bonjour le monde"
        mock_info = MagicMock()
        mock_info.duration = 3.0
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        engine._model = mock_model

        audio = np.zeros(16000 * 3, dtype=np.float32)
        result = engine.transcribe(audio)
        assert "Bonjour le monde" in result

    @patch.dict(sys.modules, {"faster_whisper": MagicMock()})
    def test_load_model_called_only_once(self):
        engine = WhisperEngine(model="base", language="fr")
        engine._load_model()
        first_model = engine._model
        engine._load_model()
        # Should be same object (not reloaded)
        assert engine._model is first_model
