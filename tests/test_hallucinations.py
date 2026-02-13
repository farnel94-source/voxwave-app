"""Tests pour src/transcription/hallucinations.py."""

import pytest

from src.transcription.hallucinations import (
    GENERIC_SHORT,
    KNOWN_HALLUCINATIONS,
    is_hallucination,
    strip_hallucination_tails,
)


class TestIsHallucination:
    """Tests detection d'hallucinations exactes."""

    @pytest.mark.parametrize("text", [
        "merci.", "Merci !", "merci",
        "sous-titrage", "Sous-titres",
        "...", "\u2026",
        "bye", "thank you",
        "merci d'avoir regarde",
        "merci de votre attention.",
        "a bientot.", "au revoir.",
    ])
    def test_known_hallucinations(self, text):
        assert is_hallucination(text) is True

    @pytest.mark.parametrize("text", [
        "oui", "non", "ok", "bien", "voil\u00e0",
        "ah", "oh", "hmm", "voila",
        "oui.", "non!", "ok?",
    ])
    def test_generic_short_hallucinations(self, text):
        assert is_hallucination(text) is True

    @pytest.mark.parametrize("text", [
        "Je vais faire un git push sur la branche main.",
        "Bonjour, comment \u00e7a va aujourd'hui ?",
        "Il faut que je finisse ce projet.",
        "Merci beaucoup pour votre aide precieuse.",
    ])
    def test_valid_text_not_hallucination(self, text):
        assert is_hallucination(text) is False

    def test_whitespace_stripped(self):
        assert is_hallucination("  merci.  ") is True

    def test_case_insensitive(self):
        assert is_hallucination("MERCI") is True
        assert is_hallucination("Sous-Titrage") is True


class TestStripHallucinationTails:
    """Tests suppression des fins de texte hallucinées."""

    def test_strip_sous_titrage(self):
        assert strip_hallucination_tails("Bonjour. Sous-titrage ST") == "Bonjour."

    def test_strip_merci_avoir_regarde(self):
        result = strip_hallucination_tails("Texte normal. Merci d'avoir regard\u00e9 !")
        assert result == "Texte normal."

    def test_strip_thanks_for_watching(self):
        result = strip_hallucination_tails("Hello world. Thanks for watching")
        assert result == "Hello world."

    def test_strip_please_subscribe(self):
        result = strip_hallucination_tails("Du texte. Please subscribe to my channel")
        assert result == "Du texte."

    def test_strip_trailing_dots(self):
        result = strip_hallucination_tails("Du texte....")
        assert result == "Du texte"

    def test_no_strip_normal_text(self):
        assert strip_hallucination_tails("Texte normal") == "Texte normal"

    def test_no_empty_result(self):
        """Si le nettoyage vide le texte, retourner l'original."""
        result = strip_hallucination_tails("Sous-titrage ST")
        assert result == "Sous-titrage ST"

    def test_case_insensitive(self):
        result = strip_hallucination_tails("Du texte. SOUS-TITRAGE FR")
        assert result == "Du texte."


class TestSetsConsistency:
    """Tests de coherence des ensembles."""

    def test_known_hallucinations_is_set(self):
        assert isinstance(KNOWN_HALLUCINATIONS, set)

    def test_generic_short_is_set(self):
        assert isinstance(GENERIC_SHORT, set)

    def test_no_overlap(self):
        """Les generics ne devraient pas etre dans les hallucinations exactes."""
        overlap = GENERIC_SHORT & KNOWN_HALLUCINATIONS
        assert len(overlap) == 0, f"Overlap: {overlap}"
