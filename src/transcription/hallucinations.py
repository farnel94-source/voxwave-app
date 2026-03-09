"""Hallucinations connues de Whisper/Groq — module centralise.

Whisper hallucine frequemment des phrases types (remerciements, sous-titres)
quand l'audio est silencieux ou trop court. Ce module regroupe toute la
logique de detection et de nettoyage.
"""

import re
from typing import Set

# Hallucinations exactes (comparaison en lowercase, stripped)
KNOWN_HALLUCINATIONS: Set[str] = {
    "merci.", "merci !",
    "sous-titrage", "sous-titres",
    "sous-titrage societe radio-canada",
    "sous-titrage société radio-canada",
    "sous-titrage st", "sous-titrage stl",
    "merci d'avoir regarde", "merci d'avoir regarde !",
    "merci d'avoir regarde cette video",
    "merci d'avoir regarde cette video !",
    "merci de votre attention",
    "merci de votre attention.",
    "a bientot", "a bientot.",
    "au revoir", "au revoir.",
    "bonjour.", "bonsoir.",
    "salut.",
    "...", "\u2026",
    "bye", "bye.",
    "thank you", "thanks",
    "thank you for watching",
    "thanks for watching",
    "et oui.", "et oui", "et non",
    "subtitles", "subtitle", "music", "musique",
    "\u266a", "\U0001f3b5",
}

# Mots generiques courts (comparaison sans ponctuation finale)
GENERIC_SHORT: Set[str] = {
    "oui", "non", "ok", "bon", "bien", "ah", "oh",
    "hmm", "hm", "ha", "voila", "voil\u00e0",
    "bonjour", "bonsoir", "salut", "pardon", "merci",
    "hello", "hey", "hi", "yeah", "yes", "no", "the", "so", "you",
    "i", "it",
}

# Patterns que Whisper/Groq hallucine en fin de transcription
HALLUCINATION_TAILS: re.Pattern = re.compile(
    r"\s*(?:"
    r"Sous-titrag[^\n]*"
    r"|Sous-titres[^\n]*"
    r"|Sous-titrage Soci\u00e9t\u00e9 Radio-Canada[^\n]*"
    r"|Merci d'avoir regard\u00e9[^\n]*"
    r"|Merci de votre attention[^\n]*"
    r"|Thanks for watching[^\n]*"
    r"|Thank you for watching[^\n]*"
    r"|Please subscribe[^\n]*"
    r"|N'oubliez pas de vous abonner[^\n]*"
    r"|\.{3,}"
    r")\s*$",
    re.IGNORECASE,
)


def is_hallucination(text: str) -> bool:
    """Detecte les hallucinations typiques de Whisper/Groq.

    Args:
        text: Texte transcrit.

    Returns:
        True si c'est probablement une hallucination.
    """
    text_lower = text.strip().lower()

    if text_lower in KNOWN_HALLUCINATIONS:
        return True

    if len(text_lower) < 15 and text_lower.count(" ") <= 2:
        stripped = text_lower.rstrip(".!? ")
        if stripped in GENERIC_SHORT:
            return True

    # Même phrase répétée 3+ fois = hallucination
    sentences = [s.strip() for s in re.split(r'[.!?]+', text_lower) if s.strip()]
    if len(sentences) >= 3 and len(set(sentences)) == 1:
        return True

    return False


def strip_hallucination_tails(text: str) -> str:
    """Supprime les hallucinations typiques de Whisper en fin de texte.

    Args:
        text: Texte brut de transcription.

    Returns:
        Texte nettoye, ou le texte original si le nettoyage le vide.
    """
    cleaned = HALLUCINATION_TAILS.sub("", text).strip()
    if cleaned:
        return cleaned
    return text
