"""Hiérarchie d'exceptions VoxTool."""


class VoxToolError(Exception):
    """Erreur de base VoxTool."""


class TranscriptionError(VoxToolError):
    """Erreur lors de la transcription audio."""


class CleaningError(VoxToolError):
    """Erreur lors du nettoyage de texte."""


class AudioCaptureError(VoxToolError):
    """Erreur lors de la capture audio."""


class LicenseError(VoxToolError):
    """Erreur liée à la licence."""
