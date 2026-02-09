"""Tests pour RegexCleaner."""

from src.cleaning.regex_cleaner import RegexCleaner


class TestRegexCleaner:
    def setup_method(self):
        self.cleaner = RegexCleaner()

    def test_empty_string(self):
        assert self.cleaner.clean("") == ""

    def test_none_input(self):
        assert self.cleaner.clean(None) == ""

    def test_remove_fillers(self):
        result = self.cleaner.clean("euh je vais faire un test")
        assert "euh" not in result.lower()
        assert "test" in result.lower()

    def test_remove_du_coup(self):
        result = self.cleaner.clean("du coup je fais ça")
        assert "du coup" not in result.lower()

    def test_preserve_english(self):
        result = self.cleaner.clean("je vais faire un git push")
        assert "git push" in result

    def test_capitalize_start(self):
        result = self.cleaner.clean("je fais un test")
        assert result[0] == "J"

    def test_add_period(self):
        result = self.cleaner.clean("je fais un test")
        assert result.endswith(".")

    def test_remove_repetitions(self):
        result = self.cleaner.clean("je je fais un test")
        assert "je je" not in result.lower()

    def test_already_clean(self):
        text = "Ceci est un texte propre."
        result = self.cleaner.clean(text)
        assert result == text

    def test_complex_case(self, raw_transcript, expected_clean):
        result = self.cleaner.clean(raw_transcript)
        # Vérifie que les fillers sont supprimés
        assert "euh" not in result.lower()
        assert "quoi" not in result.lower()
        assert "du coup" not in result.lower()
        # Vérifie que le contenu important est préservé
        assert "git push" in result
        assert "main" in result
