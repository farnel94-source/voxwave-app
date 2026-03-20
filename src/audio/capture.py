"""Capture audio depuis le microphone.

Usage:
    capture = AudioCapture(sample_rate=16000)
    capture.start()
    # ... enregistrement ...
    capture.stop()
    audio = capture.get_buffer()

    # Mode auto-stop avec Silero VAD :
    vad = SileroVAD()
    capture = AudioCapture(
        silero_vad=vad,
        on_silence_detected=lambda: print("silence détecté !"),
        silence_threshold_ms=500,
    )
"""

import logging
import threading
import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd  # pré-import pour éviter le délai au premier F8

logger = logging.getLogger(__name__)


class AudioCapture:
    """Capture audio depuis le microphone.

    Crée un stream par enregistrement (fiable, pas d'overflow).
    sounddevice est pré-importé pour un démarrage rapide.

    Supporte deux modes :
    - Push-to-talk : l'utilisateur appuie sur F8 pour arrêter.
    - Auto-stop    : Silero VAD détecte la fin de parole automatiquement.
    Les deux modes peuvent coexister simultanément.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 512,
        silence_threshold: float = 0.01,
        device_id: Optional[int] = None,
        on_speech_detected: Optional[Callable] = None,
        silero_vad: Optional[object] = None,
        on_silence_detected: Optional[Callable] = None,
        silence_threshold_ms: int = 500,
        on_auto_stop: Optional[Callable] = None,
        auto_stop_enabled: bool = False,
        auto_stop_silence_duration: float = 2.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.silence_threshold = silence_threshold
        self.device_id = device_id
        self.on_speech_detected = on_speech_detected
        # Auto-stop : VAD + callback + seuil silence
        self._silero_vad = silero_vad
        self._on_silence_detected = on_silence_detected
        self._silence_threshold_ms = silence_threshold_ms
        # Verrou pour ne déclencher on_silence_detected qu'une seule fois
        self._silence_triggered = False
        # Auto-stop amplitude-based (settings UI)
        self.on_auto_stop = on_auto_stop
        self.auto_stop_enabled = auto_stop_enabled
        self.auto_stop_silence_duration = auto_stop_silence_duration
        self._had_speech: bool = False
        self._last_speech_time: Optional[float] = None
        self._auto_stop_triggered: bool = False
        self._peak_amplitude: float = 0.0  # amplitude max vue pendant l'enregistrement
        self.buffer: list[np.ndarray] = []
        self._is_recording = False
        self._stream = None
        self._current_amplitude: float = 0.0
        logger.info(f"AudioCapture init: {sample_rate}Hz, {channels}ch, chunk={chunk_size}, device={device_id}, auto_stop={silero_vad is not None}")

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback appelé par sounddevice pour chaque chunk."""
        if status:
            logger.warning(f"Audio status: {status}")
        if self._is_recording:
            flat = indata.copy().flatten()
            self.buffer.append(flat)
            self._current_amplitude = float(np.abs(flat).mean())

            # Auto-stop amplitude-based (depuis les settings)
            if self.auto_stop_enabled and self.on_auto_stop and not self._auto_stop_triggered:
                # Seuil dynamique : 15% du pic d'amplitude observé (minimum: silence_threshold)
                # Permet de distinguer parole vs bruit de fond quel que soit le micro
                if self._current_amplitude > self._peak_amplitude:
                    self._peak_amplitude = self._current_amplitude
                speech_threshold = max(self._peak_amplitude * 0.15, self.silence_threshold)

                if self._current_amplitude > speech_threshold:
                    self._had_speech = True
                    self._last_speech_time = time.monotonic()
                elif self._had_speech and self._last_speech_time is not None:
                    silence_elapsed = time.monotonic() - self._last_speech_time
                    if silence_elapsed >= self.auto_stop_silence_duration:
                        self._auto_stop_triggered = True
                        logger.info(f"Auto-stop: {silence_elapsed:.1f}s de silence, arret auto")
                        self.on_auto_stop()

            # Auto-stop via Silero VAD (si activé)
            if (
                self._silero_vad is not None
                and self._on_silence_detected is not None
                and not self._silence_triggered
                and self.auto_stop_enabled
            ):
                self._silero_vad.process_chunk(flat, self.sample_rate)
                if self._silero_vad.detect_speech_end(
                    sample_rate=self.sample_rate,
                    silence_threshold_ms=self._silence_threshold_ms,
                ):
                    self._silence_triggered = True
                    # Appel direct — _schedule_auto_stop utilise QTimer.singleShot(0, ...)
                    # pour dispatcher vers le thread Qt principal (thread-safe)
                    self._on_silence_detected()
                    logger.info("Auto-stop : silence détecté, fin d'enregistrement")

    def start(self) -> None:
        """Démarre la capture audio."""
        self.buffer = []
        self._is_recording = True
        self._silence_triggered = False
        self._had_speech = False
        self._last_speech_time = None
        self._auto_stop_triggered = False
        self._peak_amplitude = 0.0
        # Réinitialiser les états LSTM du VAD pour le nouvel enregistrement
        if self._silero_vad is not None:
            self._silero_vad.reset_states()
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

    def update_auto_stop(self, enabled: bool, silence_duration: float) -> None:
        """Met à jour la config auto-stop sans redémarrer la capture."""
        self.auto_stop_enabled = enabled
        self.auto_stop_silence_duration = silence_duration
        self._silence_threshold_ms = int(silence_duration * 1000)
        logger.info(f"Auto-stop mis a jour: enabled={enabled}, duration={silence_duration}s ({self._silence_threshold_ms}ms)")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
