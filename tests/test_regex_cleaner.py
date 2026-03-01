"""Tests pour RegexCleaner."""

from src.cleaning.regex_cleaner import DEFAULT_FILLER_WORDS, RegexCleaner, get_filler_words


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

    def test_unknown_language_returns_empty_list(self):
        """Langue inconnue → liste vide, pas les filler words français."""
        result = get_filler_words("fi")  # finnois = langue non supportée
        assert result == [], f"Attendu [], obtenu {result}"

    def test_default_filler_words_is_empty(self):
        """DEFAULT_FILLER_WORDS doit être une liste vide."""
        assert DEFAULT_FILLER_WORDS == []

    def test_unknown_language_does_not_remove_words(self):
        """RegexCleaner avec langue inconnue ne doit rien supprimer."""
        cleaner = RegexCleaner(language="fi")
        text = "Minulla on koira"  # phrase finnoise
        result = cleaner.clean(text)
        assert "koira" in result

    def test_complex_case(self, raw_transcript, expected_clean):
        result = self.cleaner.clean(raw_transcript)
        # Vérifie que les fillers sont supprimés
        assert "euh" not in result.lower()
        assert "quoi" not in result.lower()
        assert "du coup" not in result.lower()
        # Vérifie que le contenu important est préservé
        assert "git push" in result
        assert "main" in result
