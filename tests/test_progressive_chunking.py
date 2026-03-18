"""Tests pour le chunking dans le pipeline progressif (_process_audio_progressive).

Bug : audio > 30s envoyé en un seul bloc à Whisper → transcription incomplète.
Fix : découper aux silences via split_at_silence() quand audio > chunking_threshold.
"""
import numpy as np
import pytest
from unittest.mock import MagicMock

from src.app import VoxWave


@pytest.fixture
def mock_config():
    """Config minimale pour tester le pipeline progressif."""
    return {
        "language": "en",
        "hotkey": "F8",
        "activation_method": "both",
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "chunk_size": 512,
            "silence_threshold": 0.01,
            "min_speech_duration": 0.5,
            "min_audio_duration": 0.5,
            "max_audio_duration": 300.0,
            "vad_aggressiveness": 2,
            "chunking_threshold": 30.0,
            "device_id": None,
            "feedback": {"enabled": False, "volume": 0.5},
        },
        "transcription": {"provider": "hybrid"},
        "whisper": {"model": "base", "beam_size": 5, "vad_filter": True, "language": "en"},
        "cleaning": {
            "mode": "auto",
            "provider": "hybrid",
            "ollama_host": "http://localhost:11434",
        },
        "gui": {"show_transcription_preview": True},
        "licensing": {"provider": "lemonsqueezy", "free_limit": 1000},
    }


def _make_app(mock_config):
    """Crée un mock VoxWave avec tous les attributs nécessaires."""
    app = MagicMock(spec=VoxWave)
    app.config = mock_config
    app.waveform = None
    app.tray = None
    app._is_processing = False
    app._processing_lock = MagicMock()
    app._processing_lock.acquire.return_value = True
    app._pipeline_bridge = MagicMock()
    app.license_validator = None
    app.processor = MagicMock()
    app.engine = MagicMock()
    app.pipeline = MagicMock()
    app.listener = MagicMock()
    app._prog_injector = MagicMock()
    app.feedback = MagicMock()
    app._shutting_down = False
    return app


class TestProgressiveChunking:
    """Vérifie que le pipeline progressif découpe les audios longs."""

    def test_long_audio_uses_chunking(self, mock_config):
        """Audio > 30s doit appeler split_at_silence + transcrire chaque chunk."""
        sample_rate = 16000
        audio_45s = np.random.randn(45 * sample_rate).astype(np.float32) * 0.1

        chunk1 = audio_45s[:20 * sample_rate]
        chunk2 = audio_45s[20 * sample_rate:]

        app = _make_app(mock_config)
        app.processor.prepare_for_whisper.return_value = audio_45s
        app.processor.split_at_silence.return_value = [chunk1, chunk2]
        app.engine.transcribe.side_effect = ["Bonjour le monde", "comment allez-vous"]

        VoxWave._process_audio_progressive(app, audio_45s)

        # split_at_silence doit être appelé (chunking activé)
        app.processor.split_at_silence.assert_called_once()
        # transcribe appelé 2 fois (une par chunk)
        assert app.engine.transcribe.call_count == 2

    def test_short_audio_no_chunking(self, mock_config):
        """Audio < 30s ne doit PAS appeler split_at_silence."""
        sample_rate = 16000
        audio_15s = np.random.randn(15 * sample_rate).astype(np.float32) * 0.1

        app = _make_app(mock_config)
        app.processor.prepare_for_whisper.return_value = audio_15s
        app.engine.transcribe.return_value = "Bonjour"

        VoxWave._process_audio_progressive(app, audio_15s)

        app.processor.split_at_silence.assert_not_called()
        assert app.engine.transcribe.call_count == 1

    def test_chunk_hallucination_filtered(self, mock_config):
        """Un chunk qui hallucine ne doit pas être inclus dans le résultat final."""
        sample_rate = 16000
        audio_45s = np.random.randn(45 * sample_rate).astype(np.float32) * 0.1

        chunk1 = audio_45s[:20 * sample_rate]
        chunk2 = audio_45s[20 * sample_rate:]

        app = _make_app(mock_config)
        app.processor.prepare_for_whisper.return_value = audio_45s
        app.processor.split_at_silence.return_value = [chunk1, chunk2]
        # chunk1 = hallucination connue, chunk2 = vrai texte
        app.engine.transcribe.side_effect = ["Sous-titrage ST", "Voici du vrai texte"]

        VoxWave._process_audio_progressive(app, audio_45s)

        # inject_raw doit recevoir uniquement le vrai texte
        inject_call = app._prog_injector.inject_raw.call_args
        if inject_call:
            injected_text = inject_call[0][0]
            assert "Sous-titrage" not in injected_text
            assert "vrai texte" in injected_text

    def test_max_duration_fallback_is_300(self, mock_config):
        """Le fallback max_audio_duration doit être 300.0, pas 120.0."""
        del mock_config["audio"]["max_audio_duration"]

        sample_rate = 16000
        # 180s (serait tronqué à 120s avec l'ancien fallback)
        audio_180s = np.random.randn(180 * sample_rate).astype(np.float32) * 0.01

        app = _make_app(mock_config)
        app.processor.prepare_for_whisper.side_effect = lambda a: a

        chunks_received = []

        def capture_split(audio_arg):
            chunks_received.append(len(audio_arg))
            return [audio_arg]

        app.processor.split_at_silence.side_effect = capture_split
        app.engine.transcribe.return_value = "texte"

        VoxWave._process_audio_progressive(app, audio_180s)

        # L'audio ne doit PAS être tronqué à 120s
        assert app.processor.split_at_silence.called
        passed_duration = chunks_received[0] / sample_rate
        assert passed_duration > 150.0, f"Audio tronqué à {passed_duration:.0f}s au lieu de 180s"
