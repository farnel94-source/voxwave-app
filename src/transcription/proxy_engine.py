"""Moteur de transcription via backend proxy.

Usage:
    engine = ProxyTranscriptionEngine(proxy_url="https://voxwave-backend.onrender.com")
    text = engine.transcribe(audio_array)
"""

import io
import logging
import time
import wave
from typing import Optional

import numpy as np
import requests

from src.transcription.groq_engine import _GROQ_HINTS
from src.transcription.hallucinations import is_hallucination, strip_hallucination_tails
from src.utils.exceptions import TranscriptionError

logger = logging.getLogger(__name__)


class ProxyTranscriptionEngine:
    """Moteur de transcription via backend proxy (forward vers Groq)."""

    def __init__(
        self,
        proxy_url: str,
        language: str = "fr",
        sample_rate: int = 16000,
        interface_language: Optional[str] = None,
        app_token: str = "",
    ) -> None:
        """Initialise le moteur proxy.

        Args:
            proxy_url: URL du backend proxy (ex: https://voxwave-backend.onrender.com).
            language: Langue de transcription.
            sample_rate: Taux d'échantillonnage audio.
            interface_language: Langue d'interface (hint initial en mode auto).
            app_token: Token applicatif pour authentification.
        """
        self.proxy_url = proxy_url.rstrip("/")
        self.language = language
        self.sample_rate = sample_rate
        self._interface_language = interface_language
        self._app_token = app_token
        self._circuit: Optional[object] = None
        self._last_detected_language: Optional[str] = None

    def set_circuit_breaker(self, circuit: "CircuitBreaker") -> None:
        """Attache un circuit breaker.

        Args:
            circuit: Instance de CircuitBreaker.
        """
        self._circuit = circuit

    @property
    def last_detected_language(self) -> Optional[str]:
        """Dernière langue détectée par le proxy."""
        return self._last_detected_language

    def preload(self) -> None:
        """No-op : pas de modèle local à précharger."""
        pass

    def _audio_to_wav_bytes(self, audio: np.ndarray) -> io.BytesIO:
        """Convertit un array numpy en fichier WAV en mémoire.

        Args:
            audio: Buffer audio float32 dans [-1, 1].

        Returns:
            BytesIO contenant le WAV.
        """
        buf = io.BytesIO()
        audio_clamped = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio_clamped * 32767).astype(np.int16)
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())
        buf.seek(0)
        buf.name = "audio.wav"
        return buf

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcrit un buffer audio via le backend proxy.

        Args:
            audio: Buffer audio numpy float32, 16kHz mono.

        Returns:
            Texte transcrit.

        Raises:
            TranscriptionError: Si la transcription échoue.
        """
        if self._circuit and not self._circuit.should_allow_request():
            raise TranscriptionError("Proxy indisponible (circuit breaker ouvert)")

        start = time.time()
        wav_buf = self._audio_to_wav_bytes(audio)

        # Construire les form fields
        data: dict[str, str] = {}
        if self.language and self.language != "auto":
            data["language"] = self.language

        # Hint de transcription (même logique que GroqWhisperEngine)
        if self.language == "auto":
            hint_lang = self._last_detected_language or self._interface_language
            hint = _GROQ_HINTS.get(hint_lang) if hint_lang else None
            if hint:
                data["prompt"] = hint
        else:
            hint = _GROQ_HINTS.get(self.language)
            if hint:
                data["prompt"] = hint

        headers: dict[str, str] = {}
        if self._app_token:
            headers["X-App-Token"] = self._app_token

        try:
            resp = requests.post(
                f"{self.proxy_url}/api/v1/transcribe",
                files={"file": ("audio.wav", wav_buf, "audio/wav")},
                data=data,
                headers=headers,
                timeout=30,
            )
        except requests.exceptions.Timeout:
            if self._circuit:
                self._circuit.record_network_failure()
            raise TranscriptionError("Proxy timeout (30s)")
        except requests.exceptions.ConnectionError as e:
            if self._circuit:
                self._circuit.record_network_failure()
            raise TranscriptionError(f"Proxy injoignable: {e}")
        except Exception as e:
            if self._circuit:
                self._circuit.record_failure()
            raise TranscriptionError(f"Proxy erreur: {e}")

        if resp.status_code != 200:
            if self._circuit:
                self._circuit.record_failure()
            raise TranscriptionError(f"Proxy HTTP {resp.status_code}: {resp.text[:200]}")

        result = resp.json()
        text = result.get("text", "").strip()

        # Mettre à jour la langue détectée
        detected_lang = result.get("language")
        if detected_lang:
            self._last_detected_language = detected_lang

        # Vérifier les hallucinations
        if is_hallucination(text):
            logger.warning(f"Hallucination détectée via proxy, rejeté: '{text}'")
            if self._circuit:
                self._circuit.record_success()
            return ""

        text = strip_hallucination_tails(text)
        if not text.strip():
            logger.warning("Texte entièrement supprimé par strip_hallucination_tails")
            if self._circuit:
                self._circuit.record_success()
            return ""

        if self._circuit:
            self._circuit.record_success()

        elapsed = time.time() - start
        duration = len(audio) / self.sample_rate
        logger.info(f"Proxy transcription: {elapsed:.2f}s pour {duration:.2f}s audio")
        return text
