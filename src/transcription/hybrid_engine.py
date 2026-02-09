"""Moteur de transcription hybride : Groq Cloud → fallback Whisper local.

Usage:
    engine = HybridTranscriptionEngine(config)
    text = engine.transcribe(audio_array)
"""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class HybridTranscriptionEngine:
    """Essaie Groq en priorité, fallback sur faster-whisper local."""

    def __init__(
        self,
        groq_model: str = "whisper-large-v3",
        local_model: str = "base",
        language: str = "fr",
    ) -> None:
        """Initialise les engines cloud et local.

        Args:
            groq_model: Modèle Whisper sur Groq.
            local_model: Modèle faster-whisper local.
            language: Langue de transcription.
        """
        self.language = language
        self._groq_engine: Optional[object] = None
        self._local_engine: Optional[object] = None
        self._groq_model = groq_model
        self._local_model = local_model

        self._init_groq()
        self._init_local()

    def _init_groq(self) -> None:
        """Tente d'initialiser le moteur Groq."""
        try:
            from src.transcription.groq_engine import GroqWhisperEngine
            self._groq_engine = GroqWhisperEngine(
                model=self._groq_model,
                language=self.language,
            )
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
                )
                self._local_engine._load_model()
                logger.info("Whisper local chargé (fallback)")
            except Exception as e:
                logger.error(f"Whisper local indisponible: {e}")
                return None
        return self._local_engine

    def _load_model(self) -> None:
        """No-op : le modèle local est chargé en lazy loading."""
        pass

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcrit en essayant Groq puis fallback local.

        Args:
            audio: Buffer audio numpy float32, 16kHz mono.

        Returns:
            Texte transcrit.
        """
        if self._groq_engine is not None:
            try:
                text = self._groq_engine.transcribe(audio)
                logger.info("Transcription via Groq (cloud)")
                return text
            except Exception as e:
                logger.warning(f"Groq echec, fallback local: {e}")

        local = self._get_local_engine()
        if local is not None:
            logger.info("Transcription via Whisper (local)")
            return local.transcribe(audio)

        raise RuntimeError("Aucun moteur de transcription disponible")
