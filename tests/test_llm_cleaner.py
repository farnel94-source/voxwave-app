"""Tests pour src/cleaning/llm_cleaner.py."""

from unittest.mock import patch, MagicMock

import pytest


class TestCloudLLMCleaner:
    """Tests CloudLLMCleaner."""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_init(self):
        from src.cleaning.llm_cleaner import CloudLLMCleaner
        cleaner = CloudLLMCleaner(api_key="test-key")
        assert cleaner.model == "gpt-4o-mini"

    def test_init_without_key_not_available(self):
        from src.cleaning.llm_cleaner import CloudLLMCleaner
        with patch.dict("os.environ", {}, clear=True):
            cleaner = CloudLLMCleaner(api_key=None)
            assert cleaner._available is False

    def test_clean_without_key_raises_cleaning_error(self):
        from src.cleaning.llm_cleaner import CloudLLMCleaner
        from src.utils.exceptions import CleaningError
        with patch.dict("os.environ", {}, clear=True):
            cleaner = CloudLLMCleaner(api_key=None)
            with pytest.raises(CleaningError, match="API key manquante"):
                cleaner.clean("test text")

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_clean_empty_text(self):
        from src.cleaning.llm_cleaner import CloudLLMCleaner
        cleaner = CloudLLMCleaner(api_key="test-key")
        assert cleaner.clean("") == ""
        assert cleaner.clean("   ") == ""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_clean_success(self):
        from src.cleaning.llm_cleaner import CloudLLMCleaner
        cleaner = CloudLLMCleaner(api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Texte nettoyé."

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        cleaner._client = mock_client

        result = cleaner.clean("euh texte brut")
        assert result == "Texte nettoyé."


class TestLLMCleaner:
    """Tests LLMCleaner (Ollama)."""

    def test_is_available_false_when_no_server(self):
        from src.cleaning.llm_cleaner import LLMCleaner
        cleaner = LLMCleaner(host="http://localhost:99999")
        assert cleaner.is_available() is False

    def test_clean_raises_when_unavailable(self):
        from unittest.mock import patch
        import requests as requests_lib
        from src.cleaning.llm_cleaner import LLMCleaner
        from src.utils.exceptions import CleaningError
        cleaner = LLMCleaner()
        with patch("requests.post", side_effect=requests_lib.exceptions.ConnectionError("refused")):
            with pytest.raises(CleaningError, match="Ollama indisponible"):
                cleaner.clean("test")

    def test_clean_empty(self):
        from src.cleaning.llm_cleaner import LLMCleaner
        cleaner = LLMCleaner()
        assert cleaner.clean("") == ""


class TestCleaningPipeline:
    """Tests CleaningPipeline."""

    def test_auto_mode_no_llm_applies_verbatim(self):
        from src.cleaning.llm_cleaner import CleaningPipeline
        # Mode auto sans LLM configuré → regex + _clean_verbatim
        pipeline = CleaningPipeline(mode="auto")
        result = pipeline.clean("bonjour le monde")
        assert result == "Bonjour le monde."

    def test_auto_mode_preserves_existing_punctuation(self):
        from src.cleaning.llm_cleaner import CleaningPipeline
        pipeline = CleaningPipeline(mode="auto")
        result = pipeline.clean("Déjà propre!")
        assert result == "Déjà propre!"

    def test_empty_text(self):
        from src.cleaning.llm_cleaner import CleaningPipeline
        pipeline = CleaningPipeline(mode="auto")
        assert pipeline.clean("") == ""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_auto_mode_cloud_success(self):
        from src.cleaning.llm_cleaner import CleaningPipeline
        pipeline = CleaningPipeline(
            mode="auto",
            cleaning_provider="cloud",
            cloud_model="gpt-4o-mini",
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Nettoyé."
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        pipeline._cloud_cleaner._client = mock_client

        result = pipeline.clean("euh texte brut")
        assert result == "Nettoyé."

    def test_auto_mode_regex_fallback_no_llm(self):
        from src.cleaning.llm_cleaner import CleaningPipeline
        # No cloud or local configured
        pipeline = CleaningPipeline(mode="auto", cleaning_provider="local")
        pipeline._local_cleaner = None
        result = pipeline.clean("euh je vais tester quoi")
        # Should get regex-cleaned + verbatim result
        assert "euh" not in result.lower()


class TestContextPrompts:
    """Tests pour les prompts contextuels par profil d'application."""

    def test_context_prompts_are_different(self):
        """Vérifie que chaque profil a un prompt distinct."""
        from src.cleaning.llm_cleaner import _get_system_prompt
        prompts = {
            profile: _get_system_prompt(profile)
            for profile in ["code", "casual", "email", "document", "default"]
        }
        # "code" ne doit pas appeler le LLM (None)
        assert prompts["code"] is None
        # Les autres doivent être différents
        assert prompts["casual"] != prompts["email"]
        assert prompts["email"] != prompts["default"]
        assert prompts["document"] == prompts["default"]  # document = prompt complet

    def test_clean_streaming_accepts_context_profile(self):
        """Vérifie que clean_streaming accepte context_profile sans erreur."""
        import inspect
        from src.cleaning.llm_cleaner import CloudLLMCleaner
        sig = inspect.signature(CloudLLMCleaner.clean_streaming)
        assert "context_profile" in sig.parameters

    def test_clean_streaming_code_profile_skips_llm(self):
        """Profil 'code' doit retourner le texte sans appel API."""
        from src.cleaning.llm_cleaner import CloudLLMCleaner
        cleaner = CloudLLMCleaner(api_key="fake-key")
        # Même avec _available=True, profil 'code' doit skip le LLM
        cleaner._available = True
        mock_client = MagicMock()
        cleaner._client = mock_client

        result = list(cleaner.clean_streaming("git push origin main", context_profile="code"))
        # Aucun appel API
        mock_client.chat.completions.create.assert_not_called()
        assert result == ["git push origin main"]
