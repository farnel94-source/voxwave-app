"""Nettoyage rapide du texte par regex. Temps cible : <1ms."""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Dictionnaire de filler words par langue (ISO 639-1)
FILLER_WORDS_BY_LANG: Dict[str, List[str]] = {
    "fr": [
        "euh", "heu", "hum", "ben", "bah", "genre", "du coup",
        "en fait", "tu vois", "quoi", "voilà", "comment dire",
        "alors", "bon", "enfin", "disons", "tu sais",
        "donc euh", "et euh", "mais euh",
    ],
    "en": [
        "uh", "um", "hmm", "like", "you know", "I mean",
        "sort of", "kind of", "basically", "actually",
        "literally", "right", "well", "so yeah",
        "you see", "anyway",
    ],
    "es": [
        "eh", "em", "bueno", "pues", "o sea", "este",
        "entonces", "como que", "digamos", "sabes",
        "la verdad", "en plan", "tipo",
    ],
    "de": [
        "äh", "ähm", "hmm", "also", "halt", "quasi",
        "sozusagen", "eigentlich", "naja", "genau",
        "sag mal", "weißt du", "irgendwie",
    ],
    "it": [
        "eh", "ehm", "cioè", "allora", "praticamente",
        "tipo", "diciamo", "insomma", "comunque",
        "sai", "vabbè", "in pratica",
    ],
    "pt": [
        "eh", "hum", "tipo", "então", "né", "assim",
        "basicamente", "na verdade", "quer dizer",
        "sabe", "enfim", "digamos",
    ],
    "nl": [
        "eh", "uhm", "nou", "zeg maar", "eigenlijk",
        "gewoon", "weet je", "dus", "ja",
        "even", "sowieso",
    ],
    "ja": [
        "えーと", "あの", "その", "まあ", "なんか",
        "ちょっと", "やっぱり", "一応", "とりあえず",
    ],
    "ko": [
        "음", "어", "그", "뭐", "이제", "좀",
        "약간", "그러니까", "아니",
    ],
    "zh": [
        "嗯", "那个", "就是", "然后", "这个",
        "其实", "反正", "所以说",
    ],
    "ru": [
        "э", "эм", "ну", "вот", "как бы", "типа",
        "короче", "в общем", "значит", "так сказать",
        "на самом деле",
    ],
    "ar": [
        "يعني", "هم", "اه", "طيب", "بصراحة",
        "الحقيقة", "فعلا",
    ],
    "tr": [
        "şey", "yani", "hani", "işte", "ıhm",
        "aslında", "bir nevi",
    ],
    "pl": [
        "no", "em", "tego", "znaczy", "w sumie",
        "jakby", "wiesz", "generalnie",
    ],
    "sv": [
        "eh", "öh", "liksom", "alltså", "typ",
        "du vet", "egentligen", "faktiskt",
    ],
    "da": [
        "øh", "altså", "liksom", "jo", "bare",
        "egentlig", "faktisk",
    ],
    "hi": [
        "उम", "अच्छा", "मतलब", "तो", "बस",
        "वैसे", "असल में",
    ],
}

# Fallback par défaut : liste vide (langue inconnue → rien supprimer)
DEFAULT_FILLER_WORDS: List[str] = []

REPETITION_PATTERN = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)
MULTI_SPACE = re.compile(r"\s{2,}")
SPACE_BEFORE_PUNCT = re.compile(r"\s+([.,!?;:])")
CAP_AFTER_DOT = re.compile(r"(\.\s+)([a-zéèêàâùûîïôç])")


def _build_filler_pattern(filler_words: List[str]) -> Optional[re.Pattern]:
    """Compile le pattern regex pour les mots de remplissage.

    Args:
        filler_words: Liste de mots à filtrer.

    Returns:
        Pattern compilé, ou None si la liste est vide.
    """
    if not filler_words:
        return None
    return re.compile(
        r"\b(" + "|".join(re.escape(w) for w in filler_words) + r")\b[,.]?\s*",
        re.IGNORECASE,
    )


def get_filler_words(language: str, custom_words: Optional[List[str]] = None) -> List[str]:
    """Retourne les filler words pour une langue donnée.

    Priorité : custom_words (config) > dictionnaire par langue > français par défaut.

    Args:
        language: Code langue ISO 639-1 (fr, en, es, etc.).
        custom_words: Liste custom depuis config.yaml (override).

    Returns:
        Liste de filler words à utiliser.
    """
    if custom_words:
        return custom_words
    return FILLER_WORDS_BY_LANG.get(language, [])


class RegexCleaner:
    """Nettoyeur de texte par regex.

    Supporte les filler words automatiques par langue et l'override
    dynamique quand Whisper détecte une langue différente.

    Args:
        language: Code langue ISO 639-1 (depuis config.yaml).
        filler_words: Liste custom de filler words (override config).
    """

    def __init__(
        self,
        language: str = "fr",
        filler_words: Optional[List[str]] = None,
    ) -> None:
        self._language = language
        self._custom_words = filler_words
        words = get_filler_words(language, filler_words)
        self._filler_pattern = _build_filler_pattern(words)
        logger.debug(
            "RegexCleaner: lang=%s, %d filler words",
            language, len(words),
        )

    def set_language(self, language: str) -> None:
        """Change la langue des filler words dynamiquement.

        Appelé quand Whisper détecte une langue différente de la config.
        Les custom words de la config sont ignorés dans ce cas
        (la détection auto prend le dessus).

        Args:
            language: Code langue ISO 639-1 détecté par Whisper.
        """
        if language == self._language:
            return
        self._language = language
        words = get_filler_words(language)
        self._filler_pattern = _build_filler_pattern(words)
        logger.info(
            "RegexCleaner: langue changée → %s (%d filler words)",
            language, len(words),
        )

    @property
    def language(self) -> str:
        """Langue actuellement configurée."""
        return self._language

    def clean(self, text: str) -> str:
        """Nettoie le texte : fillers, répétitions, ponctuation.

        Args:
            text: Texte brut à nettoyer.

        Returns:
            Texte nettoyé.
        """
        if not text or not text.strip():
            return ""
        result = text
        if self._filler_pattern:
            result = self._filler_pattern.sub("", result)
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
