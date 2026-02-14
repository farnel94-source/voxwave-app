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
        from src.cleaning.llm_cleaner import LLMCleaner
        cleaner = LLMCleaner(host="http://localhost:99999")
        with pytest.raises(ConnectionError):
            cleaner.clean("test")

    def test_clean_empty(self):
        from src.cleaning.llm_cleaner import LLMCleaner
        cleaner = LLMCleaner()
        assert cleaner.clean("") == ""


class TestCleaningPipeline:
    """Tests CleaningPipeline."""

    def test_verbatim_mode(self):
        from src.cleaning.llm_cleaner import CleaningPipeline
        pipeline = CleaningPipeline(mode="verbatim")
        result = pipeline.clean("bonjour le monde")
        assert result == "Bonjour le monde."

    def test_verbatim_preserves_existing_punctuation(self):
        from src.cleaning.llm_cleaner import CleaningPipeline
        pipeline = CleaningPipeline(mode="verbatim")
        result = pipeline.clean("Déjà propre!")
        assert result == "Déjà propre!"

    def test_empty_text(self):
        from src.cleaning.llm_cleaner import CleaningPipeline
        pipeline = CleaningPipeline(mode="verbatim")
        assert pipeline.clean("") == ""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_quality_mode_cloud_success(self):
        from src.cleaning.llm_cleaner import CleaningPipeline
        pipeline = CleaningPipeline(
            mode="quality",
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

    def test_quality_mode_regex_fallback(self):
        from src.cleaning.llm_cleaner import CleaningPipeline
        # No cloud or local configured
        pipeline = CleaningPipeline(mode="quality", cleaning_provider="local")
        pipeline._local_cleaner = None
        result = pipeline.clean("euh je vais tester quoi")
        # Should get regex-cleaned result
        assert "euh" not in result.lower()
