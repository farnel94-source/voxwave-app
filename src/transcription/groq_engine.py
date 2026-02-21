"""Moteur de transcription via Groq API (whisper-large-v3-turbo).

Usage:
    engine = GroqWhisperEngine()
    text = engine.transcribe(audio_array)
"""

import io
import json
import logging
import os
import time
import wave
from typing import Optional

import numpy as np

from src.transcription.hallucinations import strip_hallucination_tails
from src.utils.exceptions import TranscriptionError
from src.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class GroqWhisperEngine:
    """Moteur de transcription via Groq Cloud API."""

    def __init__(
        self,
        model: str = "whisper-large-v3-turbo",
        language: str = "fr",
        api_key: Optional[str] = None,
        sample_rate: int = 16000,
    ) -> None:
        """Initialise le moteur Groq.

        Args:
            model: Modèle Whisper sur Groq.
            language: Langue de transcription.
            api_key: Clé API Groq (ou variable d'env GROQ_API_KEY).
            sample_rate: Taux d'échantillonnage audio (depuis config.yaml).
        """
        self.model = model
        self.language = language
        self.sample_rate = sample_rate
        self.api_key = (api_key or os.getenv("GROQ_API_KEY") or "").strip()
        self._available = bool(self.api_key)
        self._circuit: Optional[object] = None
        self._last_detected_language: Optional[str] = None
        # Connexion persistante : client créé au démarrage pour éviter +200ms au premier appel
        if self._available:
            from groq import Groq
            self._client = Groq(api_key=self.api_key, timeout=10.0)
            logger.info(f"GroqWhisperEngine: model={model}, lang={language}, client prêt")
        else:
            self._client = None
            logger.warning("GROQ_API_KEY non configuree, Groq indisponible")

    def preload(self) -> None:
        """No-op : Groq n'a pas de modele local a precharger."""
        pass

    @property
    def last_detected_language(self) -> Optional[str]:
        """Dernière langue détectée par Groq."""
        return self._last_detected_language

    def _get_client(self):
        """Retourne le client Groq (connexion persistante initialisée au démarrage)."""
        return self._client

    def _audio_to_wav_bytes(self, audio: np.ndarray, sample_rate: int = 16000) -> io.BytesIO:
        """Convertit un array numpy en fichier WAV en mémoire.

        Args:
            audio: Buffer audio float32 dans [-1, 1].
            sample_rate: Taux d'échantillonnage.

        Returns:
            BytesIO contenant le WAV.
        """
        buf = io.BytesIO()
        # Clamp + conversion propre en int16 (sans wrap-around)
        audio_clamped = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio_clamped * 32767).astype(np.int16)
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())
        buf.seek(0)
        buf.name = "audio.wav"
        return buf

    @retry_with_backoff(
        max_retries=2,
        initial_delay=0.5,
        backoff_factor=2.0,
        exceptions=(Exception,),
        network_retries=0,
    )
    def _call_groq_api(self, wav_buf: io.BytesIO):
        """Appel API Groq avec retry automatique.

        Args:
            wav_buf: Buffer WAV à transcrire.

        Returns:
            Réponse de l'API Groq.
        """
        wav_buf.seek(0)
        client = self._get_client()
        return client.audio.transcriptions.create(
            file=("audio.wav", wav_buf),
            model=self.model,
            language=self.language,
            response_format="verbose_json",
            temperature=0.0,
            prompt="Transcription fidèle et exacte, mot à mot, d'une dictée vocale en français. Pas de sous-titres, pas de remerciements.",
        )

    def set_circuit_breaker(self, circuit: "CircuitBreaker") -> None:
        """Attache un circuit breaker a ce moteur.

        Args:
            circuit: Instance de CircuitBreaker.
        """
        self._circuit = circuit

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcrit un buffer audio via Groq API.

        Args:
            audio: Buffer audio numpy float32, 16kHz mono.

        Returns:
            Texte transcrit.

        Raises:
            TranscriptionError: Si la transcription échoue après retries.
        """
        if not self._available:
            raise TranscriptionError("Groq indisponible (API key manquante)")

        if self._circuit and not self._circuit.should_allow_request():
            raise TranscriptionError("Groq indisponible (circuit breaker ouvert)")

        start = time.time()
        wav_buf = self._audio_to_wav_bytes(audio, sample_rate=self.sample_rate)

        try:
            transcription = self._call_groq_api(wav_buf)
        except Exception as e:
            if self._circuit:
                from src.utils.retry import _is_network_error
                if _is_network_error(e):
                    self._circuit.record_network_failure()
                else:
                    self._circuit.record_failure()
            raise TranscriptionError(f"Groq API échouée: {e}") from e

        # Extraire le texte et vérifier la qualité
        if isinstance(transcription, str):
            try:
                data = json.loads(transcription)
                text = data.get("text", "").strip()
            except json.JSONDecodeError:
                text = transcription.strip()
        else:
            text = transcription.text.strip()
            # Vérifier les métriques de confiance si disponibles
            if hasattr(transcription, "segments") and transcription.segments:
                avg_logprob = sum(
                    s.get("avg_logprob", 0) if isinstance(s, dict) else getattr(s, "avg_logprob", 0)
                    for s in transcription.segments
                ) / len(transcription.segments)
                no_speech = max(
                    s.get("no_speech_prob", 0) if isinstance(s, dict) else getattr(s, "no_speech_prob", 0)
                    for s in transcription.segments
                )
                logger.info(f"Groq qualité: avg_logprob={avg_logprob:.2f}, no_speech_max={no_speech:.2f}")
                if no_speech > 0.7:
                    logger.warning("Probable silence détecté par Whisper, texte peu fiable")
                    return ""
                if avg_logprob < -1.0:
                    logger.warning(f"Confiance très basse ({avg_logprob:.2f}), texte peu fiable")

        # Extraire la langue détectée
        detected_lang = None
        if isinstance(transcription, str):
            try:
                detected_lang = json.loads(transcription).get("language")
            except (json.JSONDecodeError, AttributeError):
                pass
        else:
            detected_lang = getattr(transcription, "language", None)
        if detected_lang:
            self._last_detected_language = detected_lang
            if detected_lang != self.language:
                logger.info(f"Langue détectée: {detected_lang} (config: {self.language})")

        text = strip_hallucination_tails(text)
        if self._circuit:
            self._circuit.record_success()
        elapsed = time.time() - start
        duration = len(audio) / self.sample_rate
        logger.info(f"Groq transcription: {elapsed:.2f}s pour {duration:.2f}s audio")
        return text

