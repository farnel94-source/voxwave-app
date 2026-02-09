"""Valeurs par défaut de la configuration VoxTool."""

DEFAULT_CONFIG: dict = {
    "hotkey": "F8",
    "language": "fr",
    "model": "base",
    "injection": "paste",
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
        "chunk_size": 512,
        "silence_threshold": 0.01,
        "min_speech_duration": 0.5,
        "device_id": None,
        "feedback": {
            "enabled": True,
            "volume": 0.5,
        },
    },
    "transcription": {
        "provider": "hybrid",
    },
    "whisper": {
        "model": "base",
        "beam_size": 5,
        "vad_filter": True,
        "language": "fr",
    },
    "groq": {
        "model": "whisper-large-v3-turbo",
    },
    "cleaning": {
        "mode": "verbatim",
        "provider": "hybrid",
        "cloud_model": "gpt-4o-mini",
        "llm_model": "gemma3:4b",
        "llm_timeout": 5,
        "filler_words": [
            "euh", "heu", "hum", "ben", "bah", "genre",
            "du coup", "en fait", "tu vois", "quoi", "voilà",
            "comment dire",
        ],
    },
    "licensing": {
        "provider": "lemonsqueezy",
        "free_limit": 1000,
        "cache_duration": 86400,
    },
}
