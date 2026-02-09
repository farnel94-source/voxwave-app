"""Traitement et normalisation audio pour Whisper."""

import logging
import numpy as np

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Prépare l'audio brut pour Whisper."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate

    def normalize(self, audio: np.ndarray) -> np.ndarray:
        """Normalise seulement si nécessaire (évite d'amplifier le bruit)."""
        max_val = np.max(np.abs(audio))
        if max_val > 1.0:
            # Clipping : ramener dans [-1, 1]
            return audio / max_val
        if max_val < 0.01 and max_val > 0:
            # Très faible : boost léger (pas au max pour ne pas amplifier le bruit)
            return audio * (0.3 / max_val)
        # Volume normal : ne pas toucher
        return audio

    def trim_silence(self, audio: np.ndarray, frame_ms: int = 30,
                     pad_ms: int = 300) -> np.ndarray:
        """Supprime le silence au début et à la fin de l'audio.

        Le seuil est calculé dynamiquement basé sur le bruit de fond
        de l'enregistrement (pas de valeur hardcodée).

        Args:
            audio: Buffer audio float32.
            frame_ms: Taille de frame en ms.
            pad_ms: Padding à garder avant/après la parole.

        Returns:
            Audio trimé.
        """
        frame_size = int(self.sample_rate * frame_ms / 1000)
        pad_samples = int(self.sample_rate * pad_ms / 1000)

        # Calculer l'énergie par frame
        energies = []
        for i in range(0, len(audio) - frame_size, frame_size):
            frame = audio[i:i + frame_size]
            energies.append(np.abs(frame).mean())

        if not energies:
            return audio

        # Seuil dynamique : 3x l'énergie médiane (= bruit de fond)
        sorted_energies = sorted(energies)
        noise_floor = sorted_energies[len(sorted_energies) // 4]  # 25e percentile
        threshold = max(noise_floor * 3, 0.001)  # minimum absolu très bas
        logger.debug(f"VAD: noise_floor={noise_floor:.5f}, threshold={threshold:.5f}")

        # Trouver début et fin de parole
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

        # Convertir en samples avec padding
        start_sample = max(0, start_frame * frame_size - pad_samples)
        end_sample = min(len(audio), (end_frame + 1) * frame_size + pad_samples)

        trimmed = audio[start_sample:end_sample]

        # Sécurité : si on a trimé plus de 50%, c'est probablement une erreur
        if len(trimmed) < len(audio) * 0.5:
            logger.warning(f"Trim trop agressif ({len(trimmed)/len(audio)*100:.0f}%), audio original gardé")
            return audio

        trimmed_duration = len(trimmed) / self.sample_rate
        original_duration = len(audio) / self.sample_rate
        if trimmed_duration < original_duration * 0.95:
            logger.info(f"Silence trimé: {original_duration:.2f}s → {trimmed_duration:.2f}s")

        return trimmed

    def prepare_for_whisper(self, audio: np.ndarray) -> np.ndarray:
        """Prépare l'audio : float32, trimé, normalisé doucement."""
        audio = audio.astype(np.float32)
        audio = self.trim_silence(audio)
        audio = self.normalize(audio)
        logger.debug(f"Audio préparé: {len(audio)} samples, {len(audio)/self.sample_rate:.2f}s")
        return audio
