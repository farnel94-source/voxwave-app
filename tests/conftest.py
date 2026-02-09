"""Fixtures partagées pour les tests."""

import pytest
import numpy as np


@pytest.fixture
def sample_audio():
    """Audio de test: sinus 440Hz, 3 secondes, 16kHz, float32."""
    duration = 3.0
    sample_rate = 16000
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    return np.sin(2 * np.pi * 440 * t).astype(np.float32)


@pytest.fixture
def silence_audio():
    """Silence: 3 secondes."""
    return np.zeros(16000 * 3, dtype=np.float32)


@pytest.fixture
def short_audio():
    """Audio très court (0.1s) pour tester le rejet."""
    return np.zeros(1600, dtype=np.float32)


@pytest.fixture
def raw_transcript():
    return "euh du coup je vais euh faire un git push sur la branche main quoi"


@pytest.fixture
def expected_clean():
    return "Je vais faire un git push sur la branche main."


@pytest.fixture
def sample_config():
    return {
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
            "mode": "quality",
            "provider": "hybrid",
            "cloud_model": "gpt-4o-mini",
            "llm_model": "gemma3:4b",
            "llm_timeout": 5,
        },
        "licensing": {
            "provider": "lemonsqueezy",
            "free_limit": 1000,
            "cache_duration": 86400,
        },
    }


@pytest.fixture
def test_config_minimal():
    """Config minimale pour tester la validation."""
    return {
        "hotkey": "F8",
        "language": "fr",
    }
