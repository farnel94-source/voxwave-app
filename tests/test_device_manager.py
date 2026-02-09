"""Tests pour src/audio/device_manager.py."""

from unittest.mock import patch, MagicMock

import pytest

from src.audio.device_manager import AudioDeviceManager
from src.utils.exceptions import AudioCaptureError


class TestAudioDeviceManager:
    """Tests AudioDeviceManager."""

    @patch("src.audio.device_manager.sd")
    def test_list_input_devices(self, mock_sd):
        mock_sd.query_devices.return_value = [
            {"name": "Micro USB", "max_input_channels": 2, "default_samplerate": 44100.0},
            {"name": "Haut-parleurs", "max_input_channels": 0, "default_samplerate": 48000.0},
            {"name": "Micro interne", "max_input_channels": 1, "default_samplerate": 16000.0},
        ]
        devices = AudioDeviceManager.list_input_devices()
        assert len(devices) == 2
        assert devices[0]["name"] == "Micro USB"
        assert devices[1]["name"] == "Micro interne"

    @patch("src.audio.device_manager.sd")
    def test_list_input_devices_empty(self, mock_sd):
        mock_sd.query_devices.return_value = [
            {"name": "Speakers", "max_input_channels": 0, "default_samplerate": 48000.0},
        ]
        devices = AudioDeviceManager.list_input_devices()
        assert len(devices) == 0

    def test_validate_device_none_returns_none(self):
        assert AudioDeviceManager.validate_device(None) is None

    @patch("src.audio.device_manager.sd")
    def test_validate_device_valid(self, mock_sd):
        mock_sd.query_devices.return_value = {
            "name": "Micro USB",
            "max_input_channels": 2,
        }
        result = AudioDeviceManager.validate_device(0)
        assert result == 0

    @patch("src.audio.device_manager.sd")
    def test_validate_device_not_input(self, mock_sd):
        mock_sd.query_devices.return_value = {
            "name": "Speakers",
            "max_input_channels": 0,
        }
        with pytest.raises(AudioCaptureError, match="n'est pas un micro"):
            AudioDeviceManager.validate_device(1)

    @patch("src.audio.device_manager.sd")
    def test_validate_device_not_found(self, mock_sd):
        mock_sd.query_devices.side_effect = ValueError("Invalid device")
        with pytest.raises(AudioCaptureError, match="introuvable"):
            AudioDeviceManager.validate_device(999)

    @patch("src.audio.device_manager.sd")
    @patch("builtins.print")
    def test_print_devices(self, mock_print, mock_sd):
        mock_sd.query_devices.side_effect = [
            # First call: list all devices
            [
                {"name": "Micro", "max_input_channels": 1, "default_samplerate": 16000.0},
            ],
            # Second call: query default input
            {"name": "Micro"},
        ]
        AudioDeviceManager.print_devices()
        assert mock_print.called
