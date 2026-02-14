"""Tests pour src/transcription/groq_engine.py."""

import io
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from src.utils.exceptions import TranscriptionError


class TestGroqWhisperEngine:
    """Tests GroqWhisperEngine."""

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def _create_engine(self):
        from src.transcription.groq_engine import GroqWhisperEngine
        return GroqWhisperEngine(api_key="test-key")

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_init_with_api_key(self):
        engine = self._create_engine()
        assert engine.model == "whisper-large-v3-turbo"
        assert engine.language == "fr"

    def test_init_without_api_key_not_available(self):
        from src.transcription.groq_engine import GroqWhisperEngine
        with patch.dict("os.environ", {}, clear=True):
            engine = GroqWhisperEngine(api_key=None)
            assert engine._available is False

    def test_transcribe_without_api_key_raises_transcription_error(self):
        from src.transcription.groq_engine import GroqWhisperEngine
        from src.utils.exceptions import TranscriptionError
        with patch.dict("os.environ", {}, clear=True):
            engine = GroqWhisperEngine(api_key=None)
            audio = np.zeros(16000, dtype=np.float32)
            with pytest.raises(TranscriptionError, match="API key manquante"):
                engine.transcribe(audio)

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_audio_to_wav_bytes(self):
        engine = self._create_engine()
        audio = np.sin(np.linspace(0, 1, 16000)).astype(np.float32)
        wav = engine._audio_to_wav_bytes(audio)
        assert isinstance(wav, io.BytesIO)
        assert wav.name == "audio.wav"
        # WAV header starts with RIFF
        data = wav.read(4)
        assert data == b"RIFF"

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_transcribe_success(self):
        engine = self._create_engine()

        mock_response = MagicMock()
        mock_response.text = "Bonjour le monde"
        mock_response.segments = []

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response
        engine._client = mock_client

        audio = np.sin(np.linspace(0, 1, 16000)).astype(np.float32)
        result = engine.transcribe(audio)
        assert result == "Bonjour le monde"

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_transcribe_api_failure_raises_transcription_error(self):
        engine = self._create_engine()

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = ConnectionError("timeout")
        engine._client = mock_client

        audio = np.sin(np.linspace(0, 1, 16000)).astype(np.float32)
        with pytest.raises(TranscriptionError):
            engine.transcribe(audio)

    def test_strip_hallucination_tails(self):
        from src.transcription.hallucinations import strip_hallucination_tails
        assert strip_hallucination_tails("Bonjour. Sous-titrage ST") == "Bonjour."
        assert strip_hallucination_tails("Merci d'avoir regard\u00e9") == "Merci d'avoir regard\u00e9"
        assert strip_hallucination_tails("Texte normal") == "Texte normal"

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_no_speech_detection(self):
        engine = self._create_engine()

        mock_segment = MagicMock()
        mock_segment.avg_logprob = -0.5
        mock_segment.no_speech_prob = 0.9

        mock_response = MagicMock()
        mock_response.text = "merci"
        mock_response.segments = [mock_segment]

        # Make segment behave like an object (not dict)
        type(mock_segment).__contains__ = lambda self, key: False

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response
        engine._client = mock_client

        audio = np.zeros(16000, dtype=np.float32)
        result = engine.transcribe(audio)
        assert result == ""
