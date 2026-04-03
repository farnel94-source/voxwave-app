"""Moteur de transcription hybride : Groq Cloud → fallback Whisper local.

Usage:
    engine = HybridTranscriptionEngine(config)
    text = engine.transcribe(audio_array)
"""

import logging
from typing import Callable, Optional

import numpy as np

from src.utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class HybridTranscriptionEngine:
    """Essaie Groq en priorité, fallback sur faster-whisper local."""

    def __init__(
        self,
        groq_model: str = "whisper-large-v3",
        local_model: str = "base",
        language: str = "fr",
        sample_rate: int = 16000,
        on_fallback: Optional[Callable[[str], None]] = None,
        interface_language: Optional[str] = None,
        transcription_provider: str = "hybrid",
        proxy_url: Optional[str] = None,
        proxy_app_token: str = "",
    ) -> None:
        """Initialise les engines cloud et local.

        Args:
            groq_model: Modèle Whisper sur Groq.
            local_model: Modèle faster-whisper local.
            language: Langue de transcription.
            sample_rate: Taux d'échantillonnage audio (depuis config.yaml).
            on_fallback: Callback appele lors d'un fallback (message str).
            interface_language: Langue d'interface (hint initial en mode auto).
            transcription_provider: Provider (hybrid, cloud, local, proxy).
            proxy_url: URL du backend proxy (requis si provider == "proxy").
        """
        self._language = language
        self.sample_rate = sample_rate
        self.on_fallback = on_fallback
        self._interface_language = interface_language
        self._groq_engine: Optional[object] = None
        self._proxy_engine: Optional[object] = None
        self._local_engine: Optional[object] = None
        self._groq_model = groq_model
        self._local_model = local_model
        self._transcription_provider = transcription_provider
        self._proxy_url = proxy_url
        self._proxy_app_token = proxy_app_token
        self._last_detected_language: Optional[str] = None
        self._circuit = CircuitBreaker(name="groq", failure_threshold=3, cooldown_seconds=30.0)

        if proxy_url and transcription_provider in ("proxy", "hybrid"):
            self._init_proxy()
        if transcription_provider in ("hybrid", "cloud"):
            self._init_groq()
        self._init_local()

    @property
    def language(self) -> str:
        return self._language

    @language.setter
    def language(self, value: str) -> None:
        """Propage le changement de langue aux sous-moteurs."""
        self._language = value
        if self._proxy_engine and hasattr(self._proxy_engine, "language"):
            self._proxy_engine.language = value
            if value == "auto" and hasattr(self._proxy_engine, "_last_detected_language"):
                self._proxy_engine._last_detected_language = None
        if self._groq_engine and hasattr(self._groq_engine, "language"):
            self._groq_engine.language = value
            # Reset la détection pour garantir un 1er appel neutre en mode auto
            if value == "auto" and hasattr(self._groq_engine, "_last_detected_language"):
                self._groq_engine._last_detected_language = None
        if self._local_engine and hasattr(self._local_engine, "language"):
            self._local_engine.language = value
            if value == "auto" and hasattr(self._local_engine, "_last_known_language"):
                self._local_engine._last_known_language = None

    def _init_proxy(self) -> None:
        """Tente d'initialiser le moteur proxy."""
        try:
            from src.transcription.proxy_engine import ProxyTranscriptionEngine
            self._proxy_engine = ProxyTranscriptionEngine(
                proxy_url=self._proxy_url,
                language=self.language,
                sample_rate=self.sample_rate,
                interface_language=self._interface_language,
                app_token=self._proxy_app_token,
            )
            self._proxy_engine.set_circuit_breaker(self._circuit)
            logger.info(f"Proxy transcription engine initialisé ({self._proxy_url})")
        except Exception as e:
            logger.warning(f"Proxy indisponible: {e}")

    def _init_groq(self) -> None:
        """Tente d'initialiser le moteur Groq."""
        try:
            from src.transcription.groq_engine import GroqWhisperEngine
            self._groq_engine = GroqWhisperEngine(
                model=self._groq_model,
                language=self.language,
                sample_rate=self.sample_rate,
                interface_language=self._interface_language,
            )
            self._groq_engine.set_circuit_breaker(self._circuit)
            logger.info("Groq engine initialisé")
        except Exception as e:
            logger.warning(f"Groq indisponible: {e}")

    def _init_local(self) -> None:
        """Prépare le moteur Whisper local (lazy — chargé au premier fallback)."""
        logger.info("Whisper local disponible en fallback (lazy loading)")

    def _get_local_engine(self):
        """Charge le moteur local à la demande."""
        if self._local_engine is None:
            try:
                from src.transcription.whisper_engine import WhisperEngine
                self._local_engine = WhisperEngine(
                    model=self._local_model,
                    language=self.language,
                    sample_rate=self.sample_rate,
                    interface_language=self._interface_language,
                )
                self._local_engine.preload()
                logger.info("Whisper local chargé (fallback)")
            except Exception as e:
                logger.error(f"Whisper local indisponible: {e}")
                return None
        return self._local_engine

    def preload(self) -> None:
        """Precharge le moteur local si disponible."""
        if self._local_engine is not None:
            self._local_engine.preload()

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcrit en essayant proxy/Groq puis fallback local.

        Args:
            audio: Buffer audio numpy float32, 16kHz mono.

        Returns:
            Texte transcrit.
        """
        # Proxy en priorité si configuré
        if self._proxy_engine is not None:
            try:
                text = self._proxy_engine.transcribe(audio)
                self._last_detected_language = self._proxy_engine.last_detected_language
                logger.info("Transcription via proxy (backend)")
                return text
            except Exception as e:
                logger.warning(f"Proxy échec, fallback: {e}")
                if self.on_fallback:
                    self.on_fallback("Transcription : mode local (proxy indisponible)")

        if self._groq_engine is not None:
            try:
                text = self._groq_engine.transcribe(audio)
                self._last_detected_language = self._groq_engine.last_detected_language
                logger.info("Transcription via Groq (cloud)")
                return text
            except Exception as e:
                logger.warning(f"Groq echec, fallback local: {e}")
                if self.on_fallback:
                    self.on_fallback("Transcription : mode local (cloud indisponible)")

        local = self._get_local_engine()
        if local is not None:
            logger.info("Transcription via Whisper (local)")
            text = local.transcribe(audio)
            self._last_detected_language = local.last_detected_language
            return text

        raise RuntimeError("Aucun moteur de transcription disponible")

    @property
    def last_detected_language(self) -> Optional[str]:
        """Dernière langue détectée par le moteur utilisé."""
        return self._last_detected_language
