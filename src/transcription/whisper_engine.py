"""Moteur de transcription faster-whisper.

Usage:
    engine = WhisperEngine(model="base")
    text = engine.transcribe(audio_array)
"""

import logging
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class WhisperEngine:
    """Moteur de transcription faster-whisper."""

    SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large-v3"]

    def __init__(
        self,
        model: str = "base",
        language: str = "fr",
        compute_type: Optional[str] = None,
        sample_rate: int = 16000,
    ) -> None:
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Modèle '{model}' non supporté. Choix : {self.SUPPORTED_MODELS}")
        self.model_name = model
        self.language = language
        self.sample_rate = sample_rate
        self.compute_type = compute_type or self._detect_compute_type()
        self._model = None
        self._last_detected_language: Optional[str] = None
        logger.info(f"WhisperEngine: model={model}, lang={language}, compute={self.compute_type}")

    @property
    def last_detected_language(self) -> Optional[str]:
        """Dernière langue détectée par Whisper."""
        return self._last_detected_language

    def _detect_compute_type(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return "float16"
        except ImportError:
            pass
        return "int8"

    def preload(self) -> None:
        """Precharge le modele Whisper (appel public)."""
        self._load_model()

    def _load_model(self):
        if self._model is None:
            logger.info(f"Chargement modèle {self.model_name}...")
            start = time.time()
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_name,
                compute_type=self.compute_type,
            )
            logger.info(f"Modèle chargé en {time.time()-start:.2f}s")

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcrit un buffer audio en texte."""
        self._load_model()
        start = time.time()
        segments, info = self._model.transcribe(
            audio,
            beam_size=5,
            language=self.language,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=True,
        )
        text = " ".join(seg.text for seg in segments).strip()
        self._last_detected_language = getattr(info, "language", self.language)
        if self._last_detected_language != self.language:
            logger.info(f"Langue détectée: {self._last_detected_language} (config: {self.language})")
        elapsed = time.time() - start
        duration = len(audio) / self.sample_rate
        rtf = elapsed / duration if duration > 0 else 0
        logger.info(f"Transcription: {elapsed:.2f}s pour {duration:.2f}s audio (RTF={rtf:.2f})")
        return text
