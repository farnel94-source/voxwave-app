"""Hiérarchie d'exceptions VoxWave."""


class VoxWaveError(Exception):
    """Erreur de base VoxWave."""


class TranscriptionError(VoxWaveError):
    """Erreur lors de la transcription audio."""


class CleaningError(VoxWaveError):
    """Erreur lors du nettoyage de texte."""


class AudioCaptureError(VoxWaveError):
    """Erreur lors de la capture audio."""


class LicenseError(VoxWaveError):
    """Erreur liée à la licence."""
