"""Tests pour src/audio/feedback.py."""

import platform
from unittest.mock import patch, MagicMock

import pytest

from src.audio.feedback import AudioFeedback


class TestAudioFeedback:
    """Tests AudioFeedback."""

    def test_init_defaults(self):
        fb = AudioFeedback()
        assert fb.enabled is True
        assert fb.volume == 0.5

    def test_init_disabled(self):
        fb = AudioFeedback(enabled=False)
        assert fb.enabled is False

    def test_volume_clamped(self):
        fb = AudioFeedback(volume=2.0)
        assert fb.volume == 1.0
        fb2 = AudioFeedback(volume=-1.0)
        assert fb2.volume == 0.0

    def test_play_start_disabled_does_nothing(self):
        fb = AudioFeedback(enabled=False)
        # Should not raise
        fb.play_start()

    def test_play_stop_disabled_does_nothing(self):
        fb = AudioFeedback(enabled=False)
        fb.play_stop()

    def test_play_complete_disabled_does_nothing(self):
        fb = AudioFeedback(enabled=False)
        fb.play_complete()

    def test_play_error_disabled_does_nothing(self):
        fb = AudioFeedback(enabled=False)
        fb.play_error()

    @patch("src.audio.feedback.AudioFeedback._play_beep")
    def test_play_start_calls_beep(self, mock_beep):
        fb = AudioFeedback(enabled=True)
        fb._play_async = MagicMock()
        fb.play_start()
        fb._play_async.assert_called_once_with(frequency=800, duration_ms=150)

    @patch("src.audio.feedback.AudioFeedback._play_beep")
    def test_play_error_calls_beep(self, mock_beep):
        fb = AudioFeedback(enabled=True)
        fb._play_async = MagicMock()
        fb.play_error()
        fb._play_async.assert_called_once_with(frequency=300, duration_ms=300)

    @patch("winsound.Beep")
    def test_play_winsound(self, mock_beep):
        fb = AudioFeedback()
        fb._is_windows = True
        fb._play_beep(440, 100)
        mock_beep.assert_called_once_with(440, 100)

    @patch("sounddevice.play")
    @patch("sounddevice.wait")
    def test_play_sounddevice(self, mock_wait, mock_play):
        fb = AudioFeedback()
        fb._is_windows = False
        fb._play_beep(440, 100)
        mock_play.assert_called_once()
        mock_wait.assert_called_once()
