"""Tests de régression pour la logique avg_logprob dans GroqWhisperEngine.

Couvre le fix du faux positif : avg_logprob bas ne doit plus rejeter
de la vraie parole, seulement les hallucinations confirmées.
"""

import types
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.fixture
def engine():
    """Crée un GroqWhisperEngine avec une clé API factice."""
    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}):
        with patch("groq.Groq"):
            from src.transcription.groq_engine import GroqWhisperEngine
            eng = GroqWhisperEngine(api_key="test-key")
    return eng


def _make_transcription(text: str, avg_logprob: float, no_speech_prob: float):
    """Crée un objet transcription factice avec segments."""
    segment = types.SimpleNamespace(
        avg_logprob=avg_logprob,
        no_speech_prob=no_speech_prob,
    )
    return types.SimpleNamespace(
        text=text,
        segments=[segment],
        language="fr",
    )


class TestAvgLogprobFalsePositive:
    """avg_logprob bas + vraie parole → texte conservé (fix faux positif)."""

    def test_low_logprob_real_speech_kept(self, engine):
        """avg_logprob=-0.93 avec du vrai texte → conservé."""
        transcription = _make_transcription(
            text="Bonjour je veux tester la dictée vocale",
            avg_logprob=-0.93,
            no_speech_prob=0.0,
        )
        with patch.object(engine, "_call_groq_api", return_value=transcription):
            audio = np.zeros(16000 * 5, dtype=np.float32)
            result = engine.transcribe(audio)
        assert result != ""
        assert "Bonjour" in result

    def test_low_logprob_hallucination_rejected(self, engine):
        """avg_logprob=-0.93 avec hallucination → rejeté (bug #7 couvert)."""
        transcription = _make_transcription(
            text="No subtitles.",
            avg_logprob=-0.93,
            no_speech_prob=0.0,
        )
        with patch.object(engine, "_call_groq_api", return_value=transcription):
            audio = np.zeros(16000 * 2, dtype=np.float32)
            result = engine.transcribe(audio)
        assert result == ""


class TestExistingBehaviorUnchanged:
    """Vérifie que les garde-fous existants fonctionnent toujours."""

    def test_high_no_speech_rejected(self, engine):
        """no_speech_prob=0.8 → rejeté (inchangé)."""
        transcription = _make_transcription(
            text="quelque chose",
            avg_logprob=-0.3,
            no_speech_prob=0.8,
        )
        with patch.object(engine, "_call_groq_api", return_value=transcription):
            audio = np.zeros(16000 * 2, dtype=np.float32)
            result = engine.transcribe(audio)
        assert result == ""

    def test_good_logprob_kept(self, engine):
        """avg_logprob=-0.3 avec texte normal → conservé (inchangé)."""
        transcription = _make_transcription(
            text="Bonjour",
            avg_logprob=-0.3,
            no_speech_prob=0.0,
        )
        with patch.object(engine, "_call_groq_api", return_value=transcription):
            audio = np.zeros(16000 * 2, dtype=np.float32)
            result = engine.transcribe(audio)
        assert "Bonjour" in result
