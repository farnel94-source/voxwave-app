"""Gestion des périphériques audio (sélection microphone)."""

import logging
from typing import Optional

import sounddevice as sd

from src.utils.exceptions import AudioCaptureError

logger = logging.getLogger(__name__)


class AudioDeviceManager:
    """Liste et valide les périphériques d'entrée audio."""

    @staticmethod
    def list_input_devices() -> list[dict]:
        """Liste tous les périphériques d'entrée disponibles.

        Returns:
            Liste de dicts avec id, name, channels, sample_rate.
        """
        devices = sd.query_devices()
        input_devices = []
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                input_devices.append({
                    "id": i,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "sample_rate": dev["default_samplerate"],
                })
        return input_devices

    @staticmethod
    def validate_device(device_id: Optional[int]) -> Optional[int]:
        """Vérifie qu'un device_id existe et est un périphérique d'entrée.

        Args:
            device_id: ID du périphérique (None = défaut système).

        Returns:
            device_id validé ou None pour le défaut.

        Raises:
            AudioCaptureError: Si le device_id n'existe pas ou n'est pas un input.
        """
        if device_id is None:
            return None

        try:
            dev = sd.query_devices(device_id)
        except Exception as e:
            raise AudioCaptureError(f"Périphérique {device_id} introuvable: {e}") from e

        if dev["max_input_channels"] < 1:
            raise AudioCaptureError(
                f"Périphérique {device_id} ({dev['name']}) n'est pas un micro"
            )

        logger.info(f"Micro sélectionné: {dev['name']} (id={device_id})")
        return device_id

    @staticmethod
    def print_devices() -> None:
        """Affiche les périphériques d'entrée dans la console."""
        devices = AudioDeviceManager.list_input_devices()
        if not devices:
            print("Aucun périphérique d'entrée trouvé.")
            return

        default = sd.query_devices(kind="input")
        default_name = default["name"] if default else ""

        print("\nPériphériques d'entrée audio :")
        print("-" * 60)
        for dev in devices:
            marker = " *" if dev["name"] == default_name else ""
            print(f"  [{dev['id']}] {dev['name']} ({dev['channels']}ch, {int(dev['sample_rate'])}Hz){marker}")
        print("-" * 60)
        print("  * = défaut système")
        print("  Configurer dans config.yaml: audio.device_id: <id>\n")
