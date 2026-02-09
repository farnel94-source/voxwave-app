"""Tests pour AudioProcessor."""

import numpy as np
from src.audio.processor import AudioProcessor


class TestAudioProcessor:
    def setup_method(self):
        self.processor = AudioProcessor()

    def test_normalize(self, sample_audio):
        result = self.processor.normalize(sample_audio)
        assert np.max(np.abs(result)) <= 1.0

    def test_normalize_silence(self, silence_audio):
        result = self.processor.normalize(silence_audio)
        assert np.all(result == 0)

    def test_prepare_for_whisper(self, sample_audio):
        result = self.processor.prepare_for_whisper(sample_audio)
        assert result.dtype == np.float32
        assert np.max(np.abs(result)) <= 1.0
