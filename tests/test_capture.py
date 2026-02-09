"""Tests pour src/audio/capture.py."""

from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from src.audio.capture import AudioCapture


class TestAudioCapture:
    """Tests AudioCapture."""

    def test_init_defaults(self):
        with patch("src.audio.capture.sd"):
            capture = AudioCapture()
            assert capture.sample_rate == 16000
            assert capture.channels == 1
            assert capture.device_id is None
            assert capture.is_recording is False

    def test_init_with_device_id(self):
        with patch("src.audio.capture.sd"):
            capture = AudioCapture(device_id=3)
            assert capture.device_id == 3

    @patch("src.audio.capture.sd")
    def test_start_creates_stream(self, mock_sd):
        capture = AudioCapture()
        capture.start()
        assert capture.is_recording is True
        mock_sd.InputStream.assert_called_once()

    @patch("src.audio.capture.sd")
    def test_stop_closes_stream(self, mock_sd):
        capture = AudioCapture()
        capture.start()
        capture.stop()
        assert capture.is_recording is False

    def test_get_buffer_empty(self):
        with patch("src.audio.capture.sd"):
            capture = AudioCapture()
            buf = capture.get_buffer()
            assert len(buf) == 0

    def test_get_buffer_with_data(self):
        with patch("src.audio.capture.sd"):
            capture = AudioCapture()
            capture.buffer = [
                np.ones(100, dtype=np.float32),
                np.ones(100, dtype=np.float32),
            ]
            buf = capture.get_buffer()
            assert len(buf) == 200

    def test_clear_buffer(self):
        with patch("src.audio.capture.sd"):
            capture = AudioCapture()
            capture.buffer = [np.ones(100, dtype=np.float32)]
            capture.clear_buffer()
            assert len(capture.buffer) == 0

    @patch("src.audio.capture.sd")
    def test_audio_callback_records_when_recording(self, mock_sd):
        capture = AudioCapture()
        capture._is_recording = True
        data = np.ones((100, 1), dtype=np.float32)
        capture._audio_callback(data, 100, None, None)
        assert len(capture.buffer) == 1

    @patch("src.audio.capture.sd")
    def test_audio_callback_ignores_when_not_recording(self, mock_sd):
        capture = AudioCapture()
        capture._is_recording = False
        data = np.ones((100, 1), dtype=np.float32)
        capture._audio_callback(data, 100, None, None)
        assert len(capture.buffer) == 0

    @patch("src.audio.capture.sd")
    def test_context_manager(self, mock_sd):
        capture = AudioCapture()
        with capture:
            assert capture.is_recording is True
        assert capture.is_recording is False

    @patch("src.audio.capture.sd")
    def test_stream_uses_device_id(self, mock_sd):
        capture = AudioCapture(device_id=5)
        capture.start()
        call_kwargs = mock_sd.InputStream.call_args[1]
        assert call_kwargs["device"] == 5
