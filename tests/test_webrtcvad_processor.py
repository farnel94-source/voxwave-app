"""Tests pour webrtcvad dans AudioProcessor."""

from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from src.audio.processor import AudioProcessor, _float32_to_int16_bytes


class TestFloat32ToInt16Bytes:
    """Tests conversion float32 -> int16 bytes."""

    def test_zero(self):
        audio = np.zeros(480, dtype=np.float32)
        result = _float32_to_int16_bytes(audio)
        assert len(result) == 960  # 480 samples * 2 bytes

    def test_max_value(self):
        audio = np.ones(480, dtype=np.float32)
        result = _float32_to_int16_bytes(audio)
        assert len(result) == 960
        # Should be close to 32767
        int16 = np.frombuffer(result, dtype=np.int16)
        assert int16[0] == 32767

    def test_negative_value(self):
        audio = np.full(480, -1.0, dtype=np.float32)
        result = _float32_to_int16_bytes(audio)
        int16 = np.frombuffer(result, dtype=np.int16)
        assert int16[0] == -32767


class TestAudioProcessorWebrtcvad:
    """Tests AudioProcessor avec webrtcvad."""

    def test_init_with_aggressiveness(self):
        processor = AudioProcessor(vad_aggressiveness=3)
        assert processor._vad_aggressiveness == 3

    def test_init_clamps_aggressiveness(self):
        processor = AudioProcessor(vad_aggressiveness=5)
        assert processor._vad_aggressiveness == 3
        processor = AudioProcessor(vad_aggressiveness=-1)
        assert processor._vad_aggressiveness == 0

    def test_trim_silence_falls_back_to_energy(self):
        """Si webrtcvad echoue, fallback sur energie."""
        processor = AudioProcessor()
        processor._vad = None  # Force fallback

        # Audio avec silence au debut et a la fin
        sample_rate = 16000
        silence = np.zeros(sample_rate, dtype=np.float32)
        speech = np.random.randn(sample_rate * 2).astype(np.float32) * 0.5
        audio = np.concatenate([silence, speech, silence])

        result = processor._trim_silence_energy(audio)
        # Should be trimmed (shorter than original)
        assert len(result) <= len(audio)

    def test_trim_silence_energy_preserves_speech(self, sample_audio):
        """VAD energie ne doit pas supprimer tout le signal."""
        processor = AudioProcessor()
        processor._vad = None

        result = processor._trim_silence_energy(sample_audio)
        assert len(result) > 0

    def test_trim_silence_webrtcvad_falls_back_on_error(self):
        """Si webrtcvad leve une exception, fallback sur energie."""
        processor = AudioProcessor()
        mock_vad = MagicMock()
        mock_vad.is_speech.side_effect = RuntimeError("boom")
        processor._vad = mock_vad

        audio = np.random.randn(16000 * 3).astype(np.float32) * 0.5
        # Should not raise, should fall back
        result = processor.trim_silence(audio)
        assert len(result) > 0


class TestAudioProcessorClassifyFrames:
    """Tests _classify_frames."""

    def test_classify_frames_energy_fallback(self):
        processor = AudioProcessor()
        processor._vad = None

        # Create audio with known speech and silence
        sample_rate = 16000
        silence = np.zeros(sample_rate, dtype=np.float32)
        speech = np.random.randn(sample_rate).astype(np.float32) * 0.5
        audio = np.concatenate([silence, speech])

        flags = processor._classify_frames(audio)
        assert len(flags) > 0
        # At least some frames should be speech
        assert any(flags)

    def test_classify_frames_webrtcvad_error_fallback(self):
        processor = AudioProcessor()
        mock_vad = MagicMock()
        mock_vad.is_speech.side_effect = RuntimeError("boom")
        processor._vad = mock_vad

        audio = np.random.randn(16000 * 2).astype(np.float32) * 0.5
        flags = processor._classify_frames(audio)
        assert len(flags) > 0
