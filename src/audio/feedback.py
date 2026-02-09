"""Feedback audio (beeps) pour indiquer l'état de VoxTool.

Windows : winsound.Beep() (pas de dépendance).
Autres OS : sinusoïdes numpy + sounddevice.play().
"""

import logging
import platform
import threading
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class AudioFeedback:
    """Joue des sons courts pour signaler les événements."""

    def __init__(self, enabled: bool = True, volume: float = 0.5) -> None:
        """Initialise le feedback audio.

        Args:
            enabled: Active/désactive les sons.
            volume: Volume entre 0.0 et 1.0.
        """
        self.enabled = enabled
        self.volume = max(0.0, min(1.0, volume))
        self._is_windows = platform.system().lower() == "windows"
        logger.info(f"AudioFeedback: enabled={enabled}, volume={volume}")

    def play_start(self) -> None:
        """Son de début d'enregistrement (bip aigu montant)."""
        if not self.enabled:
            return
        self._play_async(frequency=800, duration_ms=150)

    def play_stop(self) -> None:
        """Son de fin d'enregistrement (bip descendant)."""
        if not self.enabled:
            return
        self._play_async(frequency=600, duration_ms=150)

    def play_complete(self) -> None:
        """Son de succès (double bip aigu)."""
        if not self.enabled:
            return
        self._play_async(frequency=1000, duration_ms=100)

    def play_error(self) -> None:
        """Son d'erreur (bip grave)."""
        if not self.enabled:
            return
        self._play_async(frequency=300, duration_ms=300)

    def _play_async(self, frequency: int, duration_ms: int) -> None:
        """Joue un son dans un thread pour ne pas bloquer.

        Args:
            frequency: Fréquence en Hz.
            duration_ms: Durée en millisecondes.
        """
        thread = threading.Thread(
            target=self._play_beep,
            args=(frequency, duration_ms),
            daemon=True,
        )
        thread.start()

    def _play_beep(self, frequency: int, duration_ms: int) -> None:
        """Joue un bip sonore.

        Args:
            frequency: Fréquence en Hz.
            duration_ms: Durée en millisecondes.
        """
        try:
            if self._is_windows:
                self._play_winsound(frequency, duration_ms)
            else:
                self._play_sounddevice(frequency, duration_ms)
        except Exception as e:
            logger.debug(f"Feedback audio échoué: {e}")

    def _play_winsound(self, frequency: int, duration_ms: int) -> None:
        """Joue via winsound (Windows uniquement).

        Args:
            frequency: Fréquence en Hz (37-32767).
            duration_ms: Durée en millisecondes.
        """
        import winsound
        winsound.Beep(frequency, duration_ms)

    def _play_sounddevice(self, frequency: int, duration_ms: int) -> None:
        """Joue via sounddevice + numpy (macOS/Linux).

        Args:
            frequency: Fréquence en Hz.
            duration_ms: Durée en millisecondes.
        """
        import sounddevice as sd

        sample_rate = 44100
        t = np.linspace(
            0, duration_ms / 1000, int(sample_rate * duration_ms / 1000), dtype=np.float32
        )
        # Sinusoïde avec fade in/out pour éviter les clics
        wave = np.sin(2 * np.pi * frequency * t) * self.volume
        fade_samples = min(int(sample_rate * 0.01), len(wave) // 4)
        if fade_samples > 0:
            fade_in = np.linspace(0, 1, fade_samples, dtype=np.float32)
            fade_out = np.linspace(1, 0, fade_samples, dtype=np.float32)
            wave[:fade_samples] *= fade_in
            wave[-fade_samples:] *= fade_out

        sd.play(wave, samplerate=sample_rate)
        sd.wait()
