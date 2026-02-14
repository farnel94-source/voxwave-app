"""Tests pour le decoupage audio en chunks."""

import numpy as np
import pytest

from src.audio.processor import AudioProcessor


class TestSplitAtSilence:
    """Tests split_at_silence."""

    def setup_method(self):
        self.processor = AudioProcessor()
        self.processor._vad = None  # Forcer fallback energie pour predictibilite
        self.sample_rate = 16000

    def test_short_audio_returns_single_chunk(self):
        """Audio <= max_chunk_s retourne un seul chunk."""
        audio = np.random.randn(self.sample_rate * 10).astype(np.float32) * 0.5
        chunks = self.processor.split_at_silence(audio, max_chunk_s=30.0)
        assert len(chunks) == 1
        assert len(chunks[0]) == len(audio)

    def test_long_audio_splits(self):
        """Audio > max_chunk_s doit etre decoupe."""
        # 60s d'audio avec des silences
        speech = np.random.randn(self.sample_rate * 15).astype(np.float32) * 0.5
        silence = np.zeros(self.sample_rate * 2, dtype=np.float32)
        audio = np.concatenate([speech, silence, speech, silence, speech, silence, speech])

        chunks = self.processor.split_at_silence(
            audio, min_chunk_s=10.0, max_chunk_s=20.0, silence_s=1.0,
        )
        assert len(chunks) >= 2

    def test_all_chunks_have_content(self):
        """Chaque chunk doit contenir de l'audio."""
        speech = np.random.randn(self.sample_rate * 12).astype(np.float32) * 0.5
        silence = np.zeros(self.sample_rate * 2, dtype=np.float32)
        audio = np.concatenate([speech, silence, speech, silence, speech])

        chunks = self.processor.split_at_silence(
            audio, min_chunk_s=5.0, max_chunk_s=15.0, silence_s=1.0,
        )
        for chunk in chunks:
            assert len(chunk) > 0

    def test_total_samples_preserved(self):
        """Le total des samples doit etre ~egal a l'original."""
        speech = np.random.randn(self.sample_rate * 15).astype(np.float32) * 0.5
        silence = np.zeros(self.sample_rate * 2, dtype=np.float32)
        audio = np.concatenate([speech, silence, speech])

        chunks = self.processor.split_at_silence(
            audio, min_chunk_s=5.0, max_chunk_s=18.0, silence_s=1.0,
        )
        total_samples = sum(len(c) for c in chunks)
        # Allow margin due to frame alignment (last frame can be partial)
        assert total_samples >= len(audio) * 0.90

    def test_exact_threshold(self):
        """Audio exactement = max_chunk_s retourne un seul chunk."""
        audio = np.random.randn(self.sample_rate * 30).astype(np.float32) * 0.5
        chunks = self.processor.split_at_silence(audio, max_chunk_s=30.0)
        assert len(chunks) == 1

    def test_silence_only_audio(self):
        """Audio de silence ne doit pas crasher."""
        audio = np.zeros(self.sample_rate * 60, dtype=np.float32)
        chunks = self.processor.split_at_silence(
            audio, min_chunk_s=10.0, max_chunk_s=30.0,
        )
        assert len(chunks) >= 1

    def test_force_cut_on_max_chunk(self):
        """Si pas de silence, force la coupe a max_chunk_s."""
        # Continuous speech (no silence)
        audio = np.random.randn(self.sample_rate * 60).astype(np.float32) * 0.5
        chunks = self.processor.split_at_silence(
            audio, min_chunk_s=10.0, max_chunk_s=20.0, silence_s=1.0,
        )
        assert len(chunks) >= 2
