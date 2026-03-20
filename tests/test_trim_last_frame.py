"""Tests pour _iter_frames et le fix des derniers mots coupés (bug #15)."""

import math

import numpy as np
import pytest

from src.audio.processor import AudioProcessor, _iter_frames


class TestIterFrames:
    """Tests unitaires pour _iter_frames."""

    def test_iter_frames_complete(self):
        """Audio qui tombe pile sur frame_size → N frames, aucun padding."""
        frame_size = 480  # 30ms à 16kHz
        n_frames = 5
        audio = np.ones(frame_size * n_frames, dtype=np.float32)

        frames = list(_iter_frames(audio, frame_size))
        assert len(frames) == n_frames
        for _, frame in frames:
            assert len(frame) == frame_size

    def test_iter_frames_incomplete(self):
        """Audio avec reste → N+1 frames, dernier zero-padded."""
        frame_size = 480
        n_complete = 3
        remainder = 100
        audio = np.ones(frame_size * n_complete + remainder, dtype=np.float32)

        frames = list(_iter_frames(audio, frame_size))
        assert len(frames) == n_complete + 1

        # Les premiers frames sont complets
        for _, frame in frames[:n_complete]:
            assert len(frame) == frame_size
            assert np.all(frame == 1.0)

        # Le dernier frame est zero-padded
        _, last_frame = frames[-1]
        assert len(last_frame) == frame_size
        assert np.all(last_frame[:remainder] == 1.0)
        assert np.all(last_frame[remainder:] == 0.0)

    def test_iter_frames_short(self):
        """Audio plus court qu'un frame → 1 frame padded."""
        frame_size = 480
        audio = np.ones(100, dtype=np.float32)

        frames = list(_iter_frames(audio, frame_size))
        assert len(frames) == 1

        _, frame = frames[0]
        assert len(frame) == frame_size
        assert np.all(frame[:100] == 1.0)
        assert np.all(frame[100:] == 0.0)

    def test_iter_frames_empty(self):
        """Audio vide → 0 frames."""
        audio = np.array([], dtype=np.float32)
        frames = list(_iter_frames(audio, 480))
        assert len(frames) == 0


class TestEnergyTrimLastSamples:
    """Vérifie que la parole dans le dernier frame incomplet est préservée."""

    def test_energy_trim_includes_last_samples(self):
        """Parole dans le dernier frame incomplet → préservée par le trim."""
        sr = 16000
        processor = AudioProcessor(sample_rate=sr)
        frame_size = int(sr * 30 / 1000)  # 480 samples

        # 3 frames de silence + 200 samples de "parole" (amplitude forte)
        silence = np.zeros(frame_size * 3, dtype=np.float32)
        speech = np.ones(200, dtype=np.float32) * 0.5  # frame incomplet avec parole
        audio = np.concatenate([silence, speech])

        trimmed = processor._trim_silence_energy(audio, frame_ms=30, pad_ms=0)

        # La parole doit être incluse (pas coupée)
        # Le trim ne doit pas retourner un array vide
        assert len(trimmed) > 0
        # Vérifie que les samples de parole sont dans le résultat
        assert np.max(np.abs(trimmed)) >= 0.4


class TestClassifyFramesCount:
    """Vérifie que _classify_frames retourne le bon nombre de flags."""

    def test_classify_frames_count_exact(self):
        """Audio pile sur frame_size → exactement N flags."""
        sr = 16000
        processor = AudioProcessor(sample_rate=sr)
        # Désactiver webrtcvad pour tester le fallback énergie
        processor._vad = None

        frame_size = int(sr * 30 / 1000)  # 480
        n_frames = 5
        audio = np.random.randn(frame_size * n_frames).astype(np.float32) * 0.1

        flags = processor._classify_frames(audio, frame_ms=30)
        assert len(flags) == n_frames

    def test_classify_frames_count_with_remainder(self):
        """Audio avec reste → ceil(len/frame_size) flags."""
        sr = 16000
        processor = AudioProcessor(sample_rate=sr)
        processor._vad = None

        frame_size = int(sr * 30 / 1000)  # 480
        total_samples = frame_size * 5 + 200  # 5 frames complets + 200 samples
        audio = np.random.randn(total_samples).astype(np.float32) * 0.1

        flags = processor._classify_frames(audio, frame_ms=30)
        expected = math.ceil(total_samples / frame_size)
        assert len(flags) == expected
