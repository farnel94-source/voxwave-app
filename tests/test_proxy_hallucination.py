"""Tests pour la détection d'hallucinations via proxy.

Le proxy_engine doit rejeter les transcriptions de faible confiance
(no_speech_prob élevé), comme le fait groq_engine en direct.
"""

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class TestProxyRejectsLowConfidence:
    """Le proxy_engine doit rejeter quand no_speech_prob > 0.7."""

    def _make_audio(self, duration: float = 2.0, sample_rate: int = 16000) -> np.ndarray:
        return np.zeros(int(duration * sample_rate), dtype=np.float32)

    def _mock_response(self, text: str, language: str = "fr",
                       no_speech_prob: float = 0.0, avg_logprob: float = -0.3):
        """Simule une réponse du backend avec scores de confiance."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "text": text,
            "language": language,
            "duration_s": 2.0,
            "no_speech_prob": no_speech_prob,
            "avg_logprob": avg_logprob,
        }
        return resp

    @patch("src.transcription.proxy_engine.requests.post")
    def test_high_no_speech_prob_rejected(self, mock_post):
        """Texte avec no_speech_prob > 0.7 doit être rejeté (silence probable)."""
        from src.transcription.proxy_engine import ProxyTranscriptionEngine

        engine = ProxyTranscriptionEngine(
            proxy_url="https://fake-backend.com",
            language="auto",
        )
        # Groq dit "probablement du silence" (no_speech_prob=0.9)
        # mais retourne quand même du texte halluciné
        mock_post.return_value = self._mock_response(
            text="སས སུ ངི སྲལ སྲ ར ལས",
            language="tibetan",
            no_speech_prob=0.9,
        )

        result = engine.transcribe(self._make_audio())
        assert result == "", "Texte avec no_speech_prob > 0.7 devrait être rejeté"

    @patch("src.transcription.proxy_engine.requests.post")
    def test_good_confidence_accepted(self, mock_post):
        """Texte avec bonne confiance doit être accepté."""
        from src.transcription.proxy_engine import ProxyTranscriptionEngine

        engine = ProxyTranscriptionEngine(
            proxy_url="https://fake-backend.com",
            language="fr",
        )
        mock_post.return_value = self._mock_response(
            text="Bonjour, comment ça va ?",
            language="fr",
            no_speech_prob=0.1,
            avg_logprob=-0.2,
        )

        result = engine.transcribe(self._make_audio())
        assert result == "Bonjour, comment ça va ?"
