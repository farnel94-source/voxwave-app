"""Nettoyage rapide du texte par regex. Temps cible : <1ms."""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

FILLER_WORDS: List[str] = [
    "euh", "heu", "hum", "ben", "bah", "genre", "du coup",
    "en fait", "tu vois", "quoi", "voilà", "comment dire",
    "alors", "bon", "enfin", "disons", "tu sais",
    "donc euh", "et euh", "mais euh",
]

FILLER_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in FILLER_WORDS) + r")\b[,.]?\s*",
    re.IGNORECASE,
)
REPETITION_PATTERN = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)
MULTI_SPACE = re.compile(r"\s{2,}")
SPACE_BEFORE_PUNCT = re.compile(r"\s+([.,!?;:])")
CAP_AFTER_DOT = re.compile(r"(\.\s+)([a-zéèêàâùûîïôç])")


class RegexCleaner:
    """Nettoyeur de texte par regex."""

    def clean(self, text: str) -> str:
        if not text or not text.strip():
            return ""
        result = text
        result = FILLER_PATTERN.sub("", result)
        result = REPETITION_PATTERN.sub(r"\1", result)
        result = MULTI_SPACE.sub(" ", result)
        result = SPACE_BEFORE_PUNCT.sub(r"\1", result)
        result = CAP_AFTER_DOT.sub(lambda m: m.group(1) + m.group(2).upper(), result)
        result = result.strip()
        if result and result[0].islower():
            result = result[0].upper() + result[1:]
        if result and result[-1] not in ".!?":
            result += "."
        return result
