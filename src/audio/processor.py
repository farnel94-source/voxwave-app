"""Traitement et normalisation audio pour Whisper."""

import logging
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Tenter d'importer webrtcvad
try:
    import webrtcvad
    _WEBRTCVAD_AVAILABLE = True
except ImportError:
    _WEBRTCVAD_AVAILABLE = False
    logger.info("webrtcvad non disponible, fallback sur VAD energie")


def _iter_frames(audio: np.ndarray, frame_size: int):
    """Itère sur tous les frames audio, y compris le dernier (zero-padded si incomplet).

    Args:
        audio: Buffer audio float32.
        frame_size: Taille d'un frame en samples.

    Yields:
        Tuple (index, frame) où frame fait toujours exactement frame_size samples.
    """
    for i in range(0, len(audio), frame_size):
        frame = audio[i:i + frame_size]
        if len(frame) < frame_size:
            # Dernier frame incomplet : zero-pad pour atteindre frame_size
            frame = np.pad(frame, (0, frame_size - len(frame)), mode="constant")
        yield i, frame


def _float32_to_int16_bytes(audio: np.ndarray) -> bytes:
    """Convertit un array float32 [-1, 1] en bytes int16 pour webrtcvad.

    Args:
        audio: Array float32.

    Returns:
        Bytes int16 little-endian.
    """
    int16_audio = (audio * 32767).astype(np.int16)
    return int16_audio.tobytes()


class AudioProcessor:
    """Prépare l'audio brut pour Whisper."""

    def __init__(self, sample_rate: int = 16000, vad_aggressiveness: int = 2) -> None:
        """Initialise le processeur audio.

        Args:
            sample_rate: Taux d'echantillonnage.
            vad_aggressiveness: Agressivite webrtcvad (0-3). 0=moins agressif, 3=plus agressif.
        """
        self.sample_rate = sample_rate
        self._vad_aggressiveness = max(0, min(3, vad_aggressiveness))
        self._vad: Optional[object] = None

        if _WEBRTCVAD_AVAILABLE:
            try:
                self._vad = webrtcvad.Vad(self._vad_aggressiveness)
                logger.info(f"webrtcvad initialise (aggressiveness={self._vad_aggressiveness})")
            except Exception as e:
                logger.warning(f"Echec init webrtcvad: {e}, fallback VAD energie")

    def normalize(self, audio: np.ndarray) -> np.ndarray:
        """Normalise seulement si nécessaire (évite d'amplifier le bruit)."""
        max_val = np.max(np.abs(audio))
        if max_val > 1.0:
            return audio / max_val
        if max_val < 0.01 and max_val > 0:
            return audio * (0.3 / max_val)
        return audio

    def trim_silence(self, audio: np.ndarray, frame_ms: int = 30,
                     pad_ms: int = 300) -> np.ndarray:
        """Supprime le silence au début et à la fin de l'audio.

        Utilise webrtcvad si disponible, sinon fallback sur VAD energie.

        Args:
            audio: Buffer audio float32.
            frame_ms: Taille de frame en ms.
            pad_ms: Padding à garder avant/après la parole.

        Returns:
            Audio trimé.
        """
        if self._vad is not None:
            try:
                return self._trim_silence_webrtcvad(audio, frame_ms, pad_ms)
            except Exception as e:
                logger.warning(f"webrtcvad echec: {e}, fallback VAD energie")

        return self._trim_silence_energy(audio, frame_ms, pad_ms)

    def _trim_silence_webrtcvad(self, audio: np.ndarray, frame_ms: int = 30,
                                 pad_ms: int = 300) -> np.ndarray:
        """Supprime le silence via webrtcvad.

        Args:
            audio: Buffer audio float32.
            frame_ms: Taille de frame en ms (10, 20, ou 30 pour webrtcvad).
            pad_ms: Padding à garder avant/après la parole.

        Returns:
            Audio trimé.
        """
        # webrtcvad requiert des frames de 10, 20, ou 30 ms
        if frame_ms not in (10, 20, 30):
            frame_ms = 30

        frame_size = int(self.sample_rate * frame_ms / 1000)
        pad_samples = int(self.sample_rate * pad_ms / 1000)

        # Classifier chaque frame comme parole ou silence
        speech_frames = []
        for _, frame in _iter_frames(audio, frame_size):
            frame_bytes = _float32_to_int16_bytes(frame)
            is_speech = self._vad.is_speech(frame_bytes, self.sample_rate)
            speech_frames.append(is_speech)

        if not speech_frames or not any(speech_frames):
            logger.info("Aucune parole detectee (webrtcvad), audio ignore")
            return np.array([], dtype=np.float32)

        # Trouver début et fin de parole
        start_frame = 0
        end_frame = len(speech_frames) - 1

        for i, is_speech in enumerate(speech_frames):
            if is_speech:
                start_frame = i
                break

        for i in range(len(speech_frames) - 1, -1, -1):
            if speech_frames[i]:
                end_frame = i
                break

        # Convertir en samples avec padding
        start_sample = max(0, start_frame * frame_size - pad_samples)
        end_sample = min(len(audio), (end_frame + 1) * frame_size + pad_samples)

        trimmed = audio[start_sample:end_sample]

        # Sécurité : si on a trimé plus de 50%, c'est probablement une erreur
        if len(trimmed) < len(audio) * 0.5:
            logger.warning(f"Trim webrtcvad trop agressif ({len(trimmed)/len(audio)*100:.0f}%), audio original gardé")
            return audio

        trimmed_duration = len(trimmed) / self.sample_rate
        original_duration = len(audio) / self.sample_rate
        if trimmed_duration < original_duration * 0.95:
            logger.info(f"Silence trimé (webrtcvad): {original_duration:.2f}s → {trimmed_duration:.2f}s")

        return trimmed

    def _trim_silence_energy(self, audio: np.ndarray, frame_ms: int = 30,
                              pad_ms: int = 300) -> np.ndarray:
        """Supprime le silence via VAD energie (fallback).

        Le seuil est calculé dynamiquement basé sur le bruit de fond
        de l'enregistrement (25e percentile × 3).

        Args:
            audio: Buffer audio float32.
            frame_ms: Taille de frame en ms.
            pad_ms: Padding à garder avant/après la parole.

        Returns:
            Audio trimé.
        """
        frame_size = int(self.sample_rate * frame_ms / 1000)
        pad_samples = int(self.sample_rate * pad_ms / 1000)

        energies = []
        for _, frame in _iter_frames(audio, frame_size):
            energies.append(np.abs(frame).mean())

        if not energies:
            return audio

        sorted_energies = sorted(energies)
        noise_floor = sorted_energies[len(sorted_energies) // 4]
        threshold = max(noise_floor * 3, 0.001)
        logger.debug(f"VAD energie: noise_floor={noise_floor:.5f}, threshold={threshold:.5f}")

        speech_detected = any(e > threshold for e in energies)
        if not speech_detected:
            logger.info("Aucune parole detectee (VAD energie), audio ignore")
            return np.array([], dtype=np.float32)

        start_frame = 0
        end_frame = len(energies) - 1

        for i, e in enumerate(energies):
            if e > threshold:
                start_frame = i
                break

        for i in range(len(energies) - 1, -1, -1):
            if energies[i] > threshold:
                end_frame = i
                break

        start_sample = max(0, start_frame * frame_size - pad_samples)
        end_sample = min(len(audio), (end_frame + 1) * frame_size + pad_samples)

        trimmed = audio[start_sample:end_sample]

        if len(trimmed) < len(audio) * 0.5:
            logger.warning(f"Trim trop agressif ({len(trimmed)/len(audio)*100:.0f}%), audio original gardé")
            return audio

        trimmed_duration = len(trimmed) / self.sample_rate
        original_duration = len(audio) / self.sample_rate
        if trimmed_duration < original_duration * 0.95:
            logger.info(f"Silence trimé: {original_duration:.2f}s → {trimmed_duration:.2f}s")

        return trimmed

    def split_at_silence(self, audio: np.ndarray, min_chunk_s: float = 10.0,
                         max_chunk_s: float = 30.0, silence_s: float = 1.0) -> List[np.ndarray]:
        """Decoupe l'audio aux silences pour traitement par chunks.

        Args:
            audio: Buffer audio float32.
            min_chunk_s: Duree minimale d'un chunk en secondes.
            max_chunk_s: Duree maximale d'un chunk en secondes.
            silence_s: Duree minimale de silence pour couper.

        Returns:
            Liste de chunks audio.
        """
        duration = len(audio) / self.sample_rate
        if duration <= max_chunk_s:
            return [audio]

        frame_ms = 30
        frame_size = int(self.sample_rate * frame_ms / 1000)
        min_chunk_frames = int(min_chunk_s * 1000 / frame_ms)
        max_chunk_frames = int(max_chunk_s * 1000 / frame_ms)
        silence_frames = int(silence_s * 1000 / frame_ms)

        # Classifier chaque frame
        speech_flags = self._classify_frames(audio, frame_ms)

        if not speech_flags:
            return [audio]

        # Trouver les points de coupure aux silences
        chunks: List[np.ndarray] = []
        chunk_start_frame = 0
        consecutive_silence = 0

        for i, is_speech in enumerate(speech_flags):
            frames_in_chunk = i - chunk_start_frame + 1

            if not is_speech:
                consecutive_silence += 1
            else:
                consecutive_silence = 0

            # Couper si on a assez de silence et le chunk est assez long
            should_cut = (
                consecutive_silence >= silence_frames
                and frames_in_chunk >= min_chunk_frames
            )
            # Forcer la coupe si le chunk est trop long
            force_cut = frames_in_chunk >= max_chunk_frames

            if should_cut or force_cut:
                # Cut at the end of current frame (include up to here)
                cut_frame = i + 1
                start_sample = chunk_start_frame * frame_size
                end_sample = min(len(audio), cut_frame * frame_size)
                if end_sample > start_sample:
                    chunks.append(audio[start_sample:end_sample])
                chunk_start_frame = cut_frame
                consecutive_silence = 0

        # Dernier chunk
        start_sample = chunk_start_frame * frame_size
        if start_sample < len(audio):
            chunks.append(audio[start_sample:])

        if not chunks:
            return [audio]

        logger.info(f"Audio decoupe en {len(chunks)} chunks: "
                     f"{[f'{len(c)/self.sample_rate:.1f}s' for c in chunks]}")
        return chunks

    def _classify_frames(self, audio: np.ndarray, frame_ms: int = 30) -> List[bool]:
        """Classifie chaque frame comme parole ou silence.

        Utilise webrtcvad si disponible, sinon VAD energie.

        Args:
            audio: Buffer audio float32.
            frame_ms: Taille de frame en ms.

        Returns:
            Liste de booleens (True = parole).
        """
        frame_size = int(self.sample_rate * frame_ms / 1000)

        if self._vad is not None:
            try:
                flags = []
                for _, frame in _iter_frames(audio, frame_size):
                    frame_bytes = _float32_to_int16_bytes(frame)
                    flags.append(self._vad.is_speech(frame_bytes, self.sample_rate))
                return flags
            except Exception as e:
                logger.warning(f"webrtcvad classify echec: {e}, fallback energie")

        # Fallback energie
        energies = []
        for _, frame in _iter_frames(audio, frame_size):
            energies.append(np.abs(frame).mean())

        if not energies:
            return []

        sorted_energies = sorted(energies)
        noise_floor = sorted_energies[len(sorted_energies) // 4]
        threshold = max(noise_floor * 3, 0.001)
        return [e > threshold for e in energies]

    def prepare_for_whisper(self, audio: np.ndarray) -> np.ndarray:
        """Prépare l'audio : float32, trimé, normalisé doucement."""
        audio = audio.astype(np.float32)
        audio = self.trim_silence(audio, pad_ms=500)
        if len(audio) == 0:
            return audio
        audio = self.normalize(audio)
        logger.debug(f"Audio préparé: {len(audio)} samples, {len(audio)/self.sample_rate:.2f}s")
        return audio
