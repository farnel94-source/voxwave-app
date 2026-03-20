"""Tests pour le bug auto-stop qui ne se déclenche jamais.

Bug #17: silence_threshold fixe (0.01) trop bas → bruit de fond considéré comme parole.
Bug #18: on_silence_detected lancé dans threading.Thread inutile.
"""

import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.audio.capture import AudioCapture


class TestAutoStopAmplitude:
    """Teste la logique auto-stop amplitude-based dans _audio_callback."""

    def _make_capture(self, silence_threshold: float = 0.01,
                      auto_stop_duration: float = 0.5) -> AudioCapture:
        """Crée un AudioCapture avec auto-stop activé."""
        capture = AudioCapture(
            sample_rate=16000,
            channels=1,
            chunk_size=512,
            silence_threshold=silence_threshold,
            on_auto_stop=MagicMock(),
            auto_stop_enabled=True,
            auto_stop_silence_duration=auto_stop_duration,
        )
        capture._is_recording = True
        return capture

    def _send_chunks(self, capture: AudioCapture, amplitude: float, n: int = 1) -> None:
        """Simule n chunks audio avec une amplitude donnée."""
        for _ in range(n):
            chunk = np.ones((capture.chunk_size, 1), dtype=np.float32) * amplitude
            capture._audio_callback(chunk, capture.chunk_size, None, None)

    def test_auto_stop_triggers_after_silence(self):
        """Auto-stop doit se déclencher après speech + silence > duration."""
        capture = self._make_capture(silence_threshold=0.01, auto_stop_duration=0.1)

        # Simuler de la parole (amplitude haute)
        self._send_chunks(capture, amplitude=0.5, n=5)
        assert capture._had_speech is True

        # Simuler du silence TOTAL (amplitude 0)
        self._send_chunks(capture, amplitude=0.0, n=1)
        time.sleep(0.15)
        self._send_chunks(capture, amplitude=0.0, n=1)

        assert capture._auto_stop_triggered is True
        capture.on_auto_stop.assert_called_once()

    def test_auto_stop_with_background_noise_dynamic_threshold(self):
        """Avec le seuil dynamique, le bruit de fond ne bloque plus l'auto-stop.

        Avant le fix: silence_threshold=0.01, bruit à 0.02 > 0.01 →
        considéré comme parole → timer reset → auto-stop jamais.
        Après le fix: seuil dynamique = 15% du pic (0.5*0.15=0.075) →
        bruit à 0.02 < 0.075 → silence → auto-stop se déclenche.
        """
        capture = self._make_capture(silence_threshold=0.01, auto_stop_duration=0.1)

        # Parole forte (pic à 0.5 → seuil dynamique = 0.075)
        self._send_chunks(capture, amplitude=0.5, n=5)
        assert capture._had_speech is True
        assert capture._peak_amplitude == pytest.approx(0.5, abs=0.01)

        # Bruit de fond à 0.02 → sous le seuil dynamique 0.075
        self._send_chunks(capture, amplitude=0.02, n=1)
        time.sleep(0.15)
        self._send_chunks(capture, amplitude=0.02, n=1)

        # Auto-stop se déclenche correctement maintenant
        assert capture._auto_stop_triggered is True
        capture.on_auto_stop.assert_called_once()

    def test_auto_stop_speech_keeps_timer_alive(self):
        """Tant qu'il y a de la parole, le timer ne s'écoule pas."""
        capture = self._make_capture(silence_threshold=0.01, auto_stop_duration=0.1)

        # Parole continue
        self._send_chunks(capture, amplitude=0.5, n=5)
        time.sleep(0.15)
        self._send_chunks(capture, amplitude=0.5, n=5)

        # Pas de silence → pas de déclenchement
        assert capture._auto_stop_triggered is False
        capture.on_auto_stop.assert_not_called()

    def test_peak_amplitude_resets_on_start(self):
        """_peak_amplitude doit se reset quand on redémarre la capture."""
        capture = self._make_capture()
        capture._peak_amplitude = 0.8

        # Simuler start() reset
        capture.buffer = []
        capture._is_recording = True
        capture._silence_triggered = False
        capture._had_speech = False
        capture._last_speech_time = None
        capture._auto_stop_triggered = False
        capture._peak_amplitude = 0.0

        assert capture._peak_amplitude == 0.0

    def test_dynamic_threshold_minimum(self):
        """Le seuil dynamique ne descend jamais en dessous de silence_threshold."""
        capture = self._make_capture(silence_threshold=0.01, auto_stop_duration=0.1)

        # Parole très faible (pic = 0.03 → 15% = 0.0045 < silence_threshold 0.01)
        self._send_chunks(capture, amplitude=0.03, n=5)

        # Le seuil doit être max(0.03*0.15, 0.01) = max(0.0045, 0.01) = 0.01
        # Donc amplitude 0.005 < 0.01 → silence
        self._send_chunks(capture, amplitude=0.005, n=1)
        time.sleep(0.15)
        self._send_chunks(capture, amplitude=0.005, n=1)

        assert capture._auto_stop_triggered is True


class TestAutoStopSileroThreadSafety:
    """Vérifie que le callback Silero ne lance pas un daemon thread."""

    def test_silero_callback_not_in_daemon_thread(self):
        """Le callback on_silence_detected ne doit PAS être lancé
        dans un threading.Thread — il doit être appelé directement
        (car _schedule_auto_stop gère déjà le dispatch Qt)."""
        import inspect
        source = inspect.getsource(AudioCapture._audio_callback)

        silero_section = source[source.find("Auto-stop via Silero"):]
        if "threading.Thread" in silero_section:
            pytest.fail(
                "on_silence_detected est encore lancé dans un threading.Thread "
                "au lieu d'être appelé directement. Comme _schedule_auto_stop "
                "utilise QTimer.singleShot(0, ...), le Thread est inutile et "
                "ajoute un niveau d'indirection dangereux."
            )
