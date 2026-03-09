"""Tests pour la détection du silence et les anti-hallucinations Whisper."""

import numpy as np
import pytest

from src.audio.processor import AudioProcessor
from src.transcription.hallucinations import is_hallucination


class TestTrimSilence:
    """Tests : trim retourne un array vide quand aucune parole détectée."""

    def setup_method(self) -> None:
        self.processor = AudioProcessor(sample_rate=16000, vad_aggressiveness=2)

    def test_trim_webrtcvad_returns_empty_on_silence(self) -> None:
        """Array de zéros → array vide (webrtcvad)."""
        silence = np.zeros(16000 * 2, dtype=np.float32)  # 2s de silence
        result = self.processor._trim_silence_webrtcvad(silence)
        assert len(result) == 0

    def test_trim_energy_returns_empty_on_silence(self) -> None:
        """Array de zéros → array vide (VAD énergie)."""
        silence = np.zeros(16000 * 2, dtype=np.float32)  # 2s de silence
        result = self.processor._trim_silence_energy(silence)
        assert len(result) == 0

    def test_prepare_for_whisper_silence_returns_short(self) -> None:
        """prepare_for_whisper(silence) retourne audio < 0.5s."""
        silence = np.zeros(16000 * 2, dtype=np.float32)
        result = self.processor.prepare_for_whisper(silence)
        duration = len(result) / 16000
        assert duration < 0.5

    def test_real_speech_not_affected(self) -> None:
        """Sinusoïde 440Hz passe normalement (pas trimée à zéro)."""
        t = np.linspace(0, 2, 16000 * 2, dtype=np.float32)
        tone = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
        result = self.processor.prepare_for_whisper(tone)
        duration = len(result) / 16000
        assert duration > 0.5, f"Audio réel trimé trop court: {duration:.2f}s"


class TestHallucinationDetection:
    """Tests : nouveaux patterns et détection de répétitions."""

    def test_hallucination_new_patterns(self) -> None:
        """Nouveaux patterns détectés comme hallucinations."""
        patterns = [
            "bonjour", "Bonjour.", "bonsoir",
            "subtitles", "Subtitle",
            "♪", "🎵",
            "sous-titrage st", "sous-titrage stl",
            "music", "musique",
            "you", "the", "i", "so", "it",
            "salut", "Salut.",
            "hello", "hey", "hi",
        ]
        for text in patterns:
            assert is_hallucination(text), f"'{text}' devrait être détecté comme hallucination"

    def test_hallucination_repetition(self) -> None:
        """Même phrase répétée 3+ fois = hallucination."""
        assert is_hallucination("Merci. Merci. Merci.")
        assert is_hallucination("Bonjour. Bonjour. Bonjour. Bonjour.")
        assert is_hallucination("Ok. Ok. Ok.")

    def test_non_hallucination_preserved(self) -> None:
        """Phrases normales ne sont pas détectées comme hallucinations."""
        normal = [
            "Je voudrais commander une pizza",
            "Il fait beau aujourd'hui et je suis content",
            "Le projet avance bien, on a terminé la première phase",
        ]
        for text in normal:
            assert not is_hallucination(text), f"'{text}' ne devrait PAS être détecté"

    def test_repetition_different_sentences_not_detected(self) -> None:
        """Phrases différentes ne déclenchent pas la détection de répétition."""
        assert not is_hallucination("Bonjour. Comment ça va. Très bien.")
