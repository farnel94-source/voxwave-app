"""Tests pour src/transcription/hybrid_engine.py."""

from unittest.mock import patch, MagicMock

import numpy as np
import pytest


class TestHybridTranscriptionEngine:
    """Tests HybridTranscriptionEngine."""

    @patch("src.transcription.hybrid_engine.HybridTranscriptionEngine._init_groq")
    @patch("src.transcription.hybrid_engine.HybridTranscriptionEngine._init_local")
    def test_transcribe_groq_success(self, mock_init_local, mock_init_groq):
        from src.transcription.hybrid_engine import HybridTranscriptionEngine

        engine = HybridTranscriptionEngine()
        mock_groq = MagicMock()
        mock_groq.transcribe.return_value = "Bonjour"
        engine._groq_engine = mock_groq

        audio = np.zeros(16000, dtype=np.float32)
        result = engine.transcribe(audio)
        assert result == "Bonjour"
        mock_groq.transcribe.assert_called_once()

    @patch("src.transcription.hybrid_engine.HybridTranscriptionEngine._init_groq")
    @patch("src.transcription.hybrid_engine.HybridTranscriptionEngine._init_local")
    def test_fallback_to_local_on_groq_failure(self, mock_init_local, mock_init_groq):
        from src.transcription.hybrid_engine import HybridTranscriptionEngine

        engine = HybridTranscriptionEngine()
        mock_groq = MagicMock()
        mock_groq.transcribe.side_effect = ConnectionError("offline")
        engine._groq_engine = mock_groq

        mock_local = MagicMock()
        mock_local.transcribe.return_value = "Fallback local"
        engine._local_engine = mock_local

        audio = np.zeros(16000, dtype=np.float32)
        result = engine.transcribe(audio)
        assert result == "Fallback local"

    @patch("src.transcription.hybrid_engine.HybridTranscriptionEngine._init_groq")
    @patch("src.transcription.hybrid_engine.HybridTranscriptionEngine._init_local")
    def test_no_engine_available_raises(self, mock_init_local, mock_init_groq):
        from src.transcription.hybrid_engine import HybridTranscriptionEngine

        engine = HybridTranscriptionEngine()
        engine._groq_engine = None
        engine._local_engine = None
        # Mock _get_local_engine to return None (simulates no local engine)
        engine._get_local_engine = lambda: None

        audio = np.zeros(16000, dtype=np.float32)
        with pytest.raises(RuntimeError, match="Aucun moteur"):
            engine.transcribe(audio)

    @patch("src.transcription.hybrid_engine.HybridTranscriptionEngine._init_groq")
    @patch("src.transcription.hybrid_engine.HybridTranscriptionEngine._init_local")
    def test_load_model_is_noop(self, mock_init_local, mock_init_groq):
        from src.transcription.hybrid_engine import HybridTranscriptionEngine

        engine = HybridTranscriptionEngine()
        # Should not raise
        engine._load_model()
