"""Détection de fin de parole en temps réel via Silero VAD (ONNX).

Le modèle ONNX (~2MB) est téléchargé automatiquement depuis GitHub
au premier lancement et mis en cache dans ~/.cache/voxtool/.

Usage:
    vad = SileroVAD(threshold=0.5)
    vad.reset_states()  # avant chaque enregistrement

    for chunk in audio_chunks:
        is_sp = vad.process_chunk(chunk, sample_rate=16000)
        if vad.detect_speech_end(sample_rate=16000, silence_threshold_ms=500):
            # fin de parole détectée !
            break
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# URL du modèle Silero VAD ONNX (repo officiel snakers4)
_MODEL_URL = (
    "https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx"
)
_MODEL_CACHE_DIR = Path.home() / ".cache" / "voxtool"
_MODEL_PATH = _MODEL_CACHE_DIR / "silero_vad.onnx"

# Silero VAD attend des chunks de taille fixe selon le sample rate
_CHUNK_SIZE_16K = 512   # 32ms à 16kHz
_CHUNK_SIZE_8K = 256    # 32ms à 8kHz


class SileroVAD:
    """Détecteur de voix temps réel via Silero VAD ONNX.

    Maintient un état LSTM interne entre les chunks — il faut appeler
    reset_states() au début de chaque nouvel enregistrement.
    """

    def __init__(self, threshold: float = 0.5) -> None:
        """Initialise le VAD et charge le modèle ONNX.

        Args:
            threshold: Seuil de probabilité (0-1) pour classer un chunk comme parole.
        """
        self.threshold = threshold
        self._session = None
        # États LSTM internes du modèle Silero (réinitialisés à chaque enregistrement)
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)
        # Compteur de chunks silencieux consécutifs
        self._consecutive_silent_chunks: int = 0
        # Indique si de la parole a déjà été détectée dans cet enregistrement
        self._had_speech: bool = False
        self._load_model()

    def _download_model(self) -> None:
        """Télécharge le modèle ONNX depuis le repo Silero officiel."""
        import urllib.request

        _MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Téléchargement Silero VAD ONNX depuis GitHub (~2MB)...")
        try:
            urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
            logger.info(f"Silero VAD téléchargé : {_MODEL_PATH}")
        except Exception as e:
            # Nettoyer le fichier partiel si le téléchargement a échoué
            if _MODEL_PATH.exists():
                _MODEL_PATH.unlink()
            raise RuntimeError(f"Impossible de télécharger Silero VAD: {e}") from e

    def _load_model(self) -> None:
        """Charge le modèle ONNX, le télécharge si absent du cache."""
        try:
            import onnxruntime as ort
        except ImportError:
            logger.warning(
                "onnxruntime non installé — Silero VAD désactivé. "
                "Installez-le : pip install onnxruntime"
            )
            return

        try:
            if not _MODEL_PATH.exists():
                self._download_model()

            # Limiter à 1 thread pour ne pas bloquer l'audio callback
            opts = ort.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 1

            self._session = ort.InferenceSession(
                str(_MODEL_PATH),
                sess_options=opts,
                providers=["CPUExecutionProvider"],
            )
            logger.info("Silero VAD ONNX chargé avec succès")
        except Exception as e:
            logger.warning(f"Echec chargement Silero VAD: {e} — fallback désactivé")
            self._session = None

    @property
    def is_available(self) -> bool:
        """Retourne True si le modèle ONNX est chargé."""
        return self._session is not None

    def reset_states(self) -> None:
        """Réinitialise les états LSTM et les compteurs.

        À appeler au début de chaque nouvel enregistrement.
        """
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)
        self._consecutive_silent_chunks = 0
        self._had_speech = False

    def process_chunk(self, chunk: np.ndarray, sample_rate: int = 16000) -> bool:
        """Traite un chunk audio et met à jour l'état interne.

        Args:
            chunk: Array float32. Doit être de taille 512 (16kHz) ou 256 (8kHz).
            sample_rate: Taux d'échantillonnage (8000 ou 16000).

        Returns:
            True si le chunk contient de la parole.
        """
        if self._session is None:
            # Fallback : on ne peut pas détecter, on assume de la parole
            return True

        try:
            audio = chunk.astype(np.float32)
            if audio.ndim == 1:
                audio = audio[np.newaxis, :]  # (1, samples)

            ort_inputs = {
                "input": audio,
                "h": self._h,
                "c": self._c,
                "sr": np.array(sample_rate, dtype=np.int64),
            }
            out, self._h, self._c = self._session.run(None, ort_inputs)
            speech_prob = float(out[0][0])
            is_sp = speech_prob >= self.threshold
        except Exception as e:
            logger.debug(f"Silero VAD process_chunk erreur: {e}")
            is_sp = True  # fallback en cas d'erreur ONNX

        # Mettre à jour les compteurs internes
        if is_sp:
            self._had_speech = True
            self._consecutive_silent_chunks = 0
        else:
            self._consecutive_silent_chunks += 1

        return is_sp

    def detect_speech_end(
        self,
        sample_rate: int = 16000,
        silence_threshold_ms: int = 500,
    ) -> bool:
        """Indique si la fin de parole a été atteinte.

        Retourne True quand au moins silence_threshold_ms ms consécutifs
        de silence ont été détectés APRÈS qu'une parole ait commencé.

        Args:
            sample_rate: Taux d'échantillonnage.
            silence_threshold_ms: Durée de silence consécutif en ms.

        Returns:
            True si fin de parole détectée.
        """
        if not self._had_speech:
            # On n'arrête pas si l'utilisateur n'a pas encore parlé
            return False

        chunk_size = _CHUNK_SIZE_16K if sample_rate == 16000 else _CHUNK_SIZE_8K
        ms_per_chunk = chunk_size / sample_rate * 1000  # ~32ms par chunk
        chunks_needed = max(1, int(silence_threshold_ms / ms_per_chunk))

        return self._consecutive_silent_chunks >= chunks_needed
