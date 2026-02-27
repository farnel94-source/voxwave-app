"""Valeurs par défaut de la configuration The Wave."""

DEFAULT_CONFIG: dict = {
    "first_launch": True,
    "hotkey": "F8",
    "language": "en",
    "activation_method": "both",
    "model": "base",
    "injection": "paste",
    "hotkey_debounce": 0.5,
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
        "chunk_size": 512,
        "silence_threshold": 0.01,
        "min_speech_duration": 0.5,
        "min_audio_duration": 0.5,
        "max_audio_duration": 120.0,
        "vad_aggressiveness": 2,
        "chunking_threshold": 30.0,
        "device_id": None,
        "auto_stop_enabled": False,
        "auto_stop_silence_duration": 2.0,
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
        "language": "en",
    },
    "groq": {
        "model": "whisper-large-v3-turbo",
    },
    # cleaning.mode: "raw" (brut, zero traitement) | "verbatim" (naturel) | "quality" (professionnel)
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
    "gui": {
        "show_transcription_preview": True,
    },
    "licensing": {
        "provider": "lemonsqueezy",
        "free_limit": 1000,
        "free_daily_limit": 50,
        "cache_duration": 86400,
    },
}
