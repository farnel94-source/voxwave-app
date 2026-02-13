"""Capture audio depuis le microphone.

Usage:
    capture = AudioCapture(sample_rate=16000)
    capture.start()
    # ... enregistrement ...
    capture.stop()
    audio = capture.get_buffer()
"""

import logging
from typing import Callable, Optional

import numpy as np
import sounddevice as sd  # pré-import pour éviter le délai au premier F8

logger = logging.getLogger(__name__)


class AudioCapture:
    """Capture audio depuis le microphone.

    Crée un stream par enregistrement (fiable, pas d'overflow).
    sounddevice est pré-importé pour un démarrage rapide.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 512,
        silence_threshold: float = 0.01,
        device_id: Optional[int] = None,
        on_speech_detected: Optional[Callable] = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.silence_threshold = silence_threshold
        self.device_id = device_id
        self.on_speech_detected = on_speech_detected
        self.buffer: list[np.ndarray] = []
        self._is_recording = False
        self._stream = None
        self._current_amplitude: float = 0.0
        logger.info(f"AudioCapture init: {sample_rate}Hz, {channels}ch, chunk={chunk_size}, device={device_id}")

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback appelé par sounddevice pour chaque chunk."""
        if status:
            logger.warning(f"Audio status: {status}")
        if self._is_recording:
            flat = indata.copy().flatten()
            self.buffer.append(flat)
            self._current_amplitude = float(np.abs(flat).mean())

    def start(self) -> None:
        """Démarre la capture audio."""
        self.buffer = []
        self._is_recording = True
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.chunk_size,
            dtype='float32',
            device=self.device_id,
            callback=self._audio_callback,
        )
        self._stream.start()
        logger.info("Capture audio démarrée")

    def stop(self) -> None:
        """Arrête la capture audio (idempotent)."""
        if not self._is_recording and self._stream is None:
            return
        self._is_recording = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Erreur fermeture stream: {e}")
            finally:
                self._stream = None
        logger.info(f"Capture arrêtée: {len(self.buffer)} chunks")

    def get_buffer(self) -> np.ndarray:
        """Retourne le buffer audio complet."""
        if not self.buffer:
            return np.array([], dtype=np.float32)
        return np.concatenate(self.buffer)

    def clear_buffer(self) -> None:
        """Vide le buffer audio."""
        self.buffer = []

    @property
    def current_amplitude(self) -> float:
        """Amplitude moyenne du dernier chunk audio (0.0 à 1.0)."""
        return self._current_amplitude

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
