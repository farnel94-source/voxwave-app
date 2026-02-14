"""Tests pour la validation de sortie LLM."""

import pytest

from src.cleaning.llm_cleaner import _validate_output, _REFORMULATION_MARKERS


class TestValidateOutput:
    """Tests _validate_output."""

    def test_valid_output(self):
        assert _validate_output(
            "euh je vais faire un git push",
            "Je vais faire un git push."
        ) is True

    def test_empty_output_rejected(self):
        assert _validate_output("some input", "") is False
        assert _validate_output("some input", "   ") is False

    def test_too_long_output_rejected(self):
        """Ratio > 1.3x => rejet."""
        input_text = "hello world"
        output_text = "Voici le texte corrige avec des ajouts supplementaires inutiles qui rallongent beaucoup"
        assert _validate_output(input_text, output_text) is False

    def test_too_short_output_rejected(self):
        """Ratio < 0.5x => rejet."""
        input_text = "euh du coup je vais faire un git push sur la branche main"
        output_text = "Git push."
        assert _validate_output(input_text, output_text) is False

    def test_acceptable_shortening(self):
        """Suppression d'hesitations = raccourcissement acceptable."""
        input_text = "euh du coup je vais faire un git push"
        output_text = "Je vais faire un git push."
        assert _validate_output(input_text, output_text) is True

    def test_reformulation_marker_voici(self):
        assert _validate_output(
            "je vais tester ca",
            "Voici le texte corrige : je vais tester ca."
        ) is False

    def test_reformulation_marker_corrige(self):
        assert _validate_output(
            "je vais tester ca",
            "Corrigé : je vais tester ca."
        ) is False

    def test_reformulation_marker_en_resume(self):
        assert _validate_output(
            "je vais tester ca bientot dans le pipeline",
            "En résumé, je vais tester ca dans le pipeline."
        ) is False

    def test_reformulation_marker_here_is(self):
        assert _validate_output(
            "I will test this soon",
            "Here is the corrected text: I will test this soon."
        ) is False

    def test_no_reformulation_in_middle(self):
        """Marqueurs au milieu du texte ne doivent pas etre detectes."""
        assert _validate_output(
            "il a dit voici mon plan",
            "Il a dit voici mon plan."
        ) is True

    def test_word_ratio_too_many_added(self):
        input_text = "faire un push"
        output_text = "Il faudrait penser a faire un push sur la branche"
        assert _validate_output(input_text, output_text) is False

    def test_word_ratio_too_many_removed(self):
        input_text = "je vais faire un git push sur la branche main puis merger"
        output_text = "Git push."
        assert _validate_output(input_text, output_text) is False

    def test_identical_input_output(self):
        text = "Bonjour le monde."
        assert _validate_output(text, text) is True

    def test_all_reformulation_markers_detected(self):
        """Verifie que tous les marqueurs sont detectes."""
        for marker in _REFORMULATION_MARKERS:
            result = _validate_output(
                "je vais tester ca bientot dans le pipeline CI",
                f"{marker.capitalize()} je vais tester ca dans le pipeline CI."
            )
            # May be False for marker detection or length ratio
            # The point is they don't return True
            assert result is False, f"Marker '{marker}' not detected"
