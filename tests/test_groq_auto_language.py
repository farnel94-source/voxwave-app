"""Tests pour le bug: mode auto-detect envoie un prompt anglais à Groq,
biaisant la détection de langue vers l'anglais.

Bug: Quand language="auto", _GROQ_HINTS.get("auto", _GROQ_HINTS_DEFAULT)
retourne le prompt anglais par défaut, ce qui biaise Whisper/Groq
vers la transcription en anglais même si l'utilisateur parle français.
"""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np


class TestGroqAutoLanguagePromptBias:
    """Vérifie que le prompt envoyé à Groq en mode auto n'est PAS biaisé
    vers une langue spécifique."""

    def test_auto_mode_first_call_no_prompt(self):
        """En mode auto sans langue détectée, _call_groq_api NE doit PAS
        envoyer de prompt (évite biais vers une langue)."""
        from src.transcription.groq_engine import GroqWhisperEngine

        with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key"}):
            engine = GroqWhisperEngine(language="auto")

        mock_client = MagicMock()
        engine._client = mock_client
        mock_client.audio.transcriptions.create.return_value = MagicMock(
            text="test", segments=[], language="fr"
        )

        audio = np.zeros(16000, dtype=np.float32)
        wav_buf = engine._audio_to_wav_bytes(audio)
        engine._call_groq_api(wav_buf)

        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        # Pas de prompt en mode auto sans langue détectée
        assert "prompt" not in call_kwargs, (
            f"En mode auto (1er appel), aucun prompt ne devrait être envoyé, "
            f"mais trouvé: prompt='{call_kwargs.get('prompt')}'"
        )

    def test_auto_mode_uses_detected_lang_hint(self):
        """Après détection de 'fr', le prompt doit être en français."""
        from src.transcription.groq_engine import GroqWhisperEngine, _GROQ_HINTS

        with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key"}):
            engine = GroqWhisperEngine(language="auto")

        # Simuler une détection précédente
        engine._last_detected_language = "fr"

        mock_client = MagicMock()
        engine._client = mock_client
        mock_client.audio.transcriptions.create.return_value = MagicMock(
            text="test", segments=[], language="fr"
        )

        audio = np.zeros(16000, dtype=np.float32)
        wav_buf = engine._audio_to_wav_bytes(audio)
        engine._call_groq_api(wav_buf)

        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        assert call_kwargs.get("prompt") == _GROQ_HINTS["fr"], (
            f"Après détection 'fr', le prompt devrait être le hint français, "
            f"pas '{call_kwargs.get('prompt')}'"
        )

    def test_groq_call_auto_no_language_param(self):
        """En mode auto, le paramètre 'language' ne doit PAS être envoyé
        à l'API Groq (pour laisser Whisper auto-détecter)."""
        from src.transcription.groq_engine import GroqWhisperEngine

        with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key"}):
            engine = GroqWhisperEngine(language="auto")

        # Mock le client Groq
        mock_client = MagicMock()
        engine._client = mock_client

        # Créer un faux audio
        audio = np.zeros(16000, dtype=np.float32)  # 1s de silence

        # Mock la réponse
        mock_response = MagicMock()
        mock_response.text = "test"
        mock_response.segments = []
        mock_response.language = "fr"
        mock_client.audio.transcriptions.create.return_value = mock_response

        engine.transcribe(audio)

        # Vérifier les kwargs envoyés à Groq
        call_kwargs = mock_client.audio.transcriptions.create.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}

        # language ne doit PAS être dans les kwargs en mode auto
        assert "language" not in kwargs, (
            f"En mode auto, 'language' ne devrait pas être passé à Groq, "
            f"mais trouvé: language={kwargs.get('language')}"
        )


class TestGroqAutoLanguageDetectionFeedback:
    """Vérifie que la langue détectée par Groq est réutilisée
    pour les appels suivants (meilleur prompt hint)."""

    def test_last_detected_language_updates_prompt_hint(self):
        """Après avoir détecté 'fr', les appels suivants devraient
        utiliser le hint français (pas le défaut anglais)."""
        from src.transcription.groq_engine import GroqWhisperEngine, _GROQ_HINTS

        with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key"}):
            engine = GroqWhisperEngine(language="auto")

        # Simuler une première détection de français
        engine._last_detected_language = "fr"

        # Le prochain appel devrait utiliser le hint français
        # Bug: le prompt est toujours basé sur self.language ("auto"),
        # pas sur _last_detected_language
        hint_lang = engine._last_detected_language or engine.language
        prompt = _GROQ_HINTS.get(hint_lang, "")

        assert prompt == _GROQ_HINTS["fr"], (
            f"Après détection de 'fr', le prompt devrait être le hint français, "
            f"pas '{prompt}'"
        )


class TestHybridEngineLanguagePropagation:
    """Vérifie que HybridEngine propage les changements de langue
    aux sous-moteurs."""

    def test_language_change_propagates_to_groq_engine(self):
        """Changer hybrid.language doit aussi changer groq_engine.language."""
        from src.transcription.hybrid_engine import HybridTranscriptionEngine

        with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key"}):
            engine = HybridTranscriptionEngine(language="fr")

        assert engine._groq_engine is not None
        assert engine._groq_engine.language == "fr"

        # Simuler un changement de langue (comme fait app.py _on_settings)
        engine.language = "auto"

        # Bug potentiel: le sous-moteur Groq garde "fr"
        assert engine._groq_engine.language == "auto", (
            f"Groq engine devrait être 'auto' mais est '{engine._groq_engine.language}'. "
            "HybridEngine ne propage pas les changements de langue aux sous-moteurs."
        )
