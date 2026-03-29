"""Test que le provider local passe bien interface_language à WhisperEngine.

Bug: app.py._create_transcription_engine() ne passait pas interface_language
quand provider=local, ce qui cassait le fallback de langue (Whisper détectait
polonais/allemand au lieu de fallback vers la langue d'interface).
"""

from unittest.mock import MagicMock, patch


def _make_app_config(provider: str = "local", language: str = "auto",
                     model: str = "base", interface_lang: str = "fr") -> dict:
    """Config minimale pour tester _create_transcription_engine."""
    return {
        "language": interface_lang,
        "whisper": {"model": model, "language": language},
        "audio": {"sample_rate": 16000},
        "groq": {"model": "whisper-large-v3-turbo"},
        "transcription": {"provider": provider},
    }


class TestLocalEngineInterfaceLanguage:
    """Vérifie que interface_language est passé en mode local."""

    @patch("src.transcription.whisper_engine.WhisperEngine.__init__", return_value=None)
    def test_local_provider_passes_interface_language(self, mock_init):
        """Bug fix: le provider local doit passer interface_language."""
        from src.app import VoxWave

        config = _make_app_config(provider="local", interface_lang="fr")

        # Appeler _create_transcription_engine directement
        app = object.__new__(VoxWave)
        app.config = config

        app._create_transcription_engine("local")

        # Vérifier que WhisperEngine a reçu interface_language
        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args
        # Doit contenir interface_language="fr"
        assert call_kwargs.kwargs.get("interface_language") == "fr" or \
            (len(call_kwargs.args) > 4 and call_kwargs.args[4] == "fr"), \
            f"interface_language non passé au WhisperEngine! Args: {call_kwargs}"

    @patch("src.transcription.whisper_engine.WhisperEngine.__init__", return_value=None)
    def test_local_provider_interface_language_defaults_to_en(self, mock_init):
        """Si pas de langue d'interface, fallback vers 'en'."""
        from src.app import VoxWave

        config = _make_app_config(provider="local")
        del config["language"]  # Pas de langue d'interface

        app = object.__new__(VoxWave)
        app.config = config

        app._create_transcription_engine("local")

        call_kwargs = mock_init.call_args
        assert call_kwargs.kwargs.get("interface_language") == "en" or \
            (len(call_kwargs.args) > 4 and call_kwargs.args[4] == "en"), \
            f"interface_language devrait fallback vers 'en'! Args: {call_kwargs}"
