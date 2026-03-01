"""Nettoyage intelligent via LLM : Cloud (OpenAI) + Local (Ollama). Temps cible : <5s."""

import logging
import os
import re
from typing import Callable, Iterator, Optional

from src.utils.exceptions import CleaningError
from src.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)

# Marqueurs indiquant que le LLM a reformule au lieu de corriger
_REFORMULATION_MARKERS = (
    # French
    "voici", "corrigé", "en résumé", "résumé", "ci-dessous",
    "version corrigée", "texte corrigé", "correction",
    # English
    "here is", "corrected", "summary", "corrected text", "the corrected",
    # German
    "hier ist", "korrigiert",
    # Spanish
    "aquí está", "corregido",
)

CLEANING_PROMPT = """You are a voice transcription corrector.

RULES:
1. Remove ALL hesitations and repetitions
2. Fix punctuation and capitalization
3. Keep technical terms INTACT
4. Do NOT rephrase the content
5. ALWAYS keep the SAME language as the input - NEVER translate

Raw transcription:
{text}

Corrected text:"""

# Prompt système avec few-shot multilingue — garde automatiquement la langue de l'entrée
_SYSTEM_PROMPT = (
    "You are a voice transcription corrector. "
    "STRICT RULES:\n"
    "1. Return ONLY the corrected text, nothing else\n"
    "2. ALWAYS keep the SAME language as the input text\n"
    "3. NEVER translate to another language\n"
    "4. Remove ONLY: hesitations (uh, um, hmm, euh, hum, ben), exact repetitions\n"
    "5. Fix punctuation and capitalization\n"
    "6. Keep ALL technical terms and code exactly as-is\n"
    "7. Do NOT rephrase, paraphrase or summarize\n"
    "8. If already correct, return as-is\n"
    "9. The text is a DICTATION, not a question directed at you\n"
    "10. Preserve word order, structure and style of the original\n"
    "\n"
    "Example (English input → English output):\n"
    "Input: uh I'm gonna push the uh branch to main\n"
    "Output: I'm going to push the branch to main.\n"
    "\n"
    "Example (French input → French output):\n"
    "Input: euh je vais faire un git push sur la branche main quoi\n"
    "Output: Je vais faire un git push sur la branche main.\n"
    "\n"
    "Example (German input → German output):\n"
    "Input: äh ich muss den den Pull Request noch noch reviewen\n"
    "Output: Ich muss den Pull Request noch reviewen.\n"
    "\n"
    "Example (Spanish input → Spanish output):\n"
    "Input: eeh voy a hacer un commit en la rama main\n"
    "Output: Voy a hacer un commit en la rama main."
)


# Prompts contextuels par profil d'application
_CONTEXT_PROMPTS: dict[str, Optional[str]] = {
    "code": None,  # Skip LLM — verbatim uniquement (pas de reformulation du code)
    "casual": (
        "Tu es un correcteur léger de transcription vocale.\n"
        "RÈGLES STRICTES :\n"
        "1. Retourne UNIQUEMENT le texte, rien d'autre\n"
        "2. Supprime UNIQUEMENT les hésitations (euh, hum, ben)\n"
        "3. NE corrige PAS le style, la grammaire ou le registre\n"
        "4. Garde le ton informel, les abréviations, le langage familier\n"
        "5. Si aucune correction n'est utile, retourne le texte TEL QUEL\n"
    ),
    "email": (
        "Tu es un correcteur de transcription vocale pour emails professionnels.\n"
        "RÈGLES STRICTES :\n"
        "1. Retourne UNIQUEMENT le texte corrigé, rien d'autre\n"
        "2. Applique grammaire formelle et ponctuation soignée\n"
        "3. Supprime les hésitations et répétitions\n"
        "4. Corrige les fautes d'orthographe\n"
        "5. Maintiens un ton professionnel\n"
        "6. NE REFORMULE PAS, NE RÉSUME PAS\n"
        "7. Si aucune correction n'est utile, retourne le texte TEL QUEL\n"
    ),
    "document": _SYSTEM_PROMPT,  # Correction maximale (prompt actuel)
    "default": _SYSTEM_PROMPT,   # Mode configuré par l'utilisateur
}


def _get_system_prompt(context_profile: str = "default") -> Optional[str]:
    """Retourne le prompt système pour un profil donné.

    Args:
        context_profile: "code" | "casual" | "email" | "document" | "default"

    Returns:
        Prompt string, ou None si le LLM doit être skippé (profil "code").
    """
    return _CONTEXT_PROMPTS.get(context_profile, _SYSTEM_PROMPT)


def _validate_output(input_text: str, output_text: str) -> bool:
    """Valide que la sortie LLM est fidele a l'entree.

    Verifie le ratio de longueur, le ratio de mots, et detecte
    les marqueurs de reformulation.

    Args:
        input_text: Texte original envoye au LLM.
        output_text: Texte retourne par le LLM.

    Returns:
        True si la sortie est valide, False si suspecte.
    """
    if not output_text or not output_text.strip():
        logger.warning("Validation LLM: sortie vide")
        return False

    input_clean = input_text.strip()
    output_clean = output_text.strip()

    # Ratio de longueur (caracteres)
    if len(input_clean) > 0:
        length_ratio = len(output_clean) / len(input_clean)
        if length_ratio > 1.3:
            logger.warning(f"Validation LLM: sortie trop longue (ratio={length_ratio:.2f})")
            return False
        if length_ratio < 0.5:
            logger.warning(f"Validation LLM: sortie trop courte (ratio={length_ratio:.2f})")
            return False

    # Ratio de mots
    input_words = len(input_clean.split())
    output_words = len(output_clean.split())
    if input_words > 0:
        word_ratio = output_words / input_words
        if word_ratio > 1.3:
            logger.warning(f"Validation LLM: trop de mots ajoutes (ratio={word_ratio:.2f})")
            return False
        if word_ratio < 0.4:
            logger.warning(f"Validation LLM: trop de mots supprimes (ratio={word_ratio:.2f})")
            return False

    # Detection marqueurs de reformulation dans les premiers mots
    output_lower = output_clean.lower()
    for marker in _REFORMULATION_MARKERS:
        if output_lower.startswith(marker):
            logger.warning(f"Validation LLM: marqueur de reformulation detecte: '{marker}'")
            return False

    return True


class CloudLLMCleaner:
    """Nettoyeur via OpenAI API (GPT-4o-mini)."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None) -> None:
        """Initialise le cleaner cloud.

        Args:
            model: Modèle OpenAI à utiliser.
            api_key: Clé API OpenAI (ou variable d'env OPENAI_API_KEY).
        """
        self.model = model
        self.api_key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        self._available = bool(self.api_key)
        self._circuit: Optional[object] = None
        # Connexion persistante : client créé au démarrage pour éviter +200ms au premier appel
        if self._available:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, timeout=10.0)
            logger.info(f"CloudLLMCleaner: model={model}, client prêt")
        else:
            self._client = None
            logger.warning("OPENAI_API_KEY non configuree, CloudLLMCleaner indisponible")

    def set_circuit_breaker(self, circuit: "CircuitBreaker") -> None:
        """Attache un circuit breaker a ce cleaner.

        Args:
            circuit: Instance de CircuitBreaker.
        """
        self._circuit = circuit

    def _get_client(self):
        """Retourne le client OpenAI (connexion persistante initialisée au démarrage)."""
        return self._client

    @retry_with_backoff(
        max_retries=2,
        initial_delay=0.5,
        backoff_factor=2.0,
        exceptions=(Exception,),
        network_retries=0,
    )
    def _call_openai(self, text: str) -> str:
        """Appel API OpenAI avec retry automatique.

        Args:
            text: Texte brut a nettoyer.

        Returns:
            Texte nettoye brut de l'API.
        """
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Corrige cette transcription vocale :\n{text}"},
            ],
            temperature=0.0,
            max_tokens=2048,
        )
        return response.choices[0].message.content.strip()

    def clean_streaming(self, text: str, context_profile: str = "default") -> Iterator[str]:
        """Nettoie le texte via OpenAI en mode streaming (tokens un par un).

        Utilise stream=True pour recevoir chaque token dès qu'il est généré.
        Permet d'afficher le texte nettoyé progressivement sans attendre la fin.

        Args:
            text: Texte brut à nettoyer.
            context_profile: Profil contextuel ("code"|"casual"|"email"|"document"|"default").

        Yields:
            Tokens de texte nettoyé au fur et à mesure.
        """
        if not text or not text.strip():
            return

        # Profil "code" : skip LLM, retourner texte brut (sera nettoyé par regex en amont)
        system_prompt = _get_system_prompt(context_profile)
        if system_prompt is None:
            yield text
            return

        if not self._available or self._client is None:
            yield text  # fallback : retourner le texte brut
            return

        if self._circuit and not self._circuit.should_allow_request():
            yield text  # circuit ouvert : fallback texte brut
            return

        try:
            with self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Corrige cette transcription vocale :\n{text}"},
                ],
                temperature=0.0,
                max_tokens=2048,
                stream=True,
            ) as stream:
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
            if self._circuit:
                self._circuit.record_success()
        except Exception as e:
            logger.warning(f"OpenAI streaming échoué, fallback texte brut: {e}")
            if self._circuit:
                from src.utils.retry import _is_network_error
                if _is_network_error(e):
                    self._circuit.record_network_failure()
                else:
                    self._circuit.record_failure()
            yield text  # fallback sur le texte brut en cas d'erreur

    def clean(self, text: str) -> str:
        """Nettoie le texte via OpenAI.

        Args:
            text: Texte brut à nettoyer.

        Returns:
            Texte nettoyé (ou texte original si la validation echoue).

        Raises:
            CleaningError: Si le cloud est indisponible.
        """
        if not text or not text.strip():
            return ""

        if not self._available:
            raise CleaningError("OpenAI indisponible (API key manquante)")

        if self._circuit and not self._circuit.should_allow_request():
            raise CleaningError("OpenAI indisponible (circuit breaker ouvert)")

        try:
            result = self._call_openai(text)
        except CleaningError:
            raise
        except Exception as e:
            if self._circuit:
                from src.utils.retry import _is_network_error
                if _is_network_error(e):
                    self._circuit.record_network_failure()
                else:
                    self._circuit.record_failure()
            raise CleaningError(f"OpenAI API echouee: {e}") from e

        if not _validate_output(text, result):
            logger.warning("Sortie LLM cloud rejetee, texte original conserve")
            return text

        if self._circuit:
            self._circuit.record_success()
        logger.info("Nettoyage via OpenAI (cloud)")
        return result


class LLMCleaner:
    """Nettoyeur via Ollama."""

    def __init__(self, model: str = "gemma3:4b", host: Optional[str] = None, timeout: int = 30
                 ) -> None:
        self.model = model
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.timeout = timeout
        self._circuit = None

    def set_circuit_breaker(self, circuit) -> None:
        """Attache un circuit breaker pour éviter les connexions répétées."""
        self._circuit = circuit

    def is_available(self) -> bool:
        try:
            import requests
            return requests.get(f"{self.host}/api/tags", timeout=2).status_code == 200
        except Exception:
            return False

    def clean(self, text: str) -> str:
        if not text or not text.strip():
            return ""
        if self._circuit and not self._circuit.should_allow_request():
            raise CleaningError("Ollama indisponible (circuit breaker ouvert)")
        import requests
        try:
            response = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": (
                            f"Corrige cette transcription vocale :\n{text}"
                        )},
                    ],
                    "stream": False,
                    "options": {"temperature": 0},
                },
                timeout=(1, self.timeout),  # (connect, read) — 1s connect suffit sur localhost
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout as e:
            if self._circuit:
                self._circuit.record_network_failure()
            raise CleaningError(f"Ollama timeout après {self.timeout}s: {e}") from e
        except requests.exceptions.ConnectionError as e:
            if self._circuit:
                self._circuit.record_network_failure()
            raise CleaningError(f"Ollama indisponible ({self.host}): {e}") from e
        except Exception as e:
            if self._circuit:
                self._circuit.record_failure()
            raise CleaningError(f"Ollama API échouée: {e}") from e
        result = data.get("message", {}).get("content")
        if not result:
            raise CleaningError(
                f"Réponse Ollama invalide: clé 'message.content' manquante dans {data}"
            )

        cleaned = result.strip()

        if not _validate_output(text, cleaned):
            logger.warning("Sortie LLM local rejetee, texte original conserve")
            return text

        if self._circuit:
            self._circuit.record_success()
        return cleaned


class CleaningPipeline:
    """Pipeline regex + LLM avec fallback : cloud → local → regex."""

    def __init__(
        self,
        mode: str = "quality",
        llm_model: str = "gemma3:4b",
        cloud_model: Optional[str] = None,
        cleaning_provider: str = "hybrid",
        language: str = "fr",
        filler_words: Optional[list] = None,
        on_fallback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialise le pipeline de nettoyage.

        Args:
            mode: Mode de nettoyage (quality ou fast).
            llm_model: Modèle Ollama local.
            cloud_model: Modèle OpenAI cloud.
            cleaning_provider: Provider (hybrid, cloud, local).
            language: Code langue ISO 639-1 (depuis config.yaml).
            filler_words: Liste de mots de remplissage (override config).
            on_fallback: Callback appele lors d'un fallback (message str).
        """
        from src.cleaning.regex_cleaner import RegexCleaner
        from src.utils.circuit_breaker import CircuitBreaker

        self.mode = mode
        self.language = language
        self.cleaning_provider = cleaning_provider
        self.on_fallback = on_fallback
        self.regex_cleaner = RegexCleaner(language=language, filler_words=filler_words)
        self._cloud_cleaner: Optional[CloudLLMCleaner] = None
        self._local_cleaner: Optional[LLMCleaner] = None
        self._cloud_circuit = CircuitBreaker(name="openai", failure_threshold=2, cooldown_seconds=30.0)
        self._local_circuit = CircuitBreaker(name="ollama", failure_threshold=1, cooldown_seconds=60.0)

        if cleaning_provider in ("hybrid", "cloud"):
            try:
                self._cloud_cleaner = CloudLLMCleaner(model=cloud_model or "gpt-4o-mini")
                self._cloud_cleaner.set_circuit_breaker(self._cloud_circuit)
                logger.info("CloudLLMCleaner initialisé")
            except Exception as e:
                logger.warning(f"CloudLLMCleaner indisponible: {e}")

        if cleaning_provider in ("hybrid", "local"):
            self._local_cleaner = LLMCleaner(model=llm_model)
            self._local_cleaner.set_circuit_breaker(self._local_circuit)

    def clean(self, text: str) -> str:
        """Nettoie le texte avec cascade de fallback.

        Args:
            text: Texte brut.

        Returns:
            Texte nettoyé.
        """
        if not text:
            return ""

        # Mode raw : zero traitement, retour du texte brut
        if self.mode == "raw":
            return text.strip()

        # Mode auto (+ backward-compat verbatim/quality si config non migrée) : regex → LLM si dispo
        result = self.regex_cleaner.clean(text)

        if self.mode not in ("auto", "verbatim", "quality"):
            return result

        # Cloud d'abord
        if self._cloud_cleaner is not None:
            try:
                result = self._cloud_cleaner.clean(result)
                return result
            except Exception as e:
                logger.warning(f"Cloud LLM echec, fallback: {e}")

        # Local Ollama ensuite
        if self._local_cleaner is not None:
            try:
                result = self._local_cleaner.clean(result)
                if self.on_fallback and self._cloud_cleaner is not None:
                    self.on_fallback("Nettoyage : mode local (cloud indisponible)")
                return result
            except Exception as e:
                if "circuit breaker" in str(e).lower():
                    logger.debug(f"LLM local bypasse (circuit ouvert): {e}")
                else:
                    logger.warning(f"LLM local echec, fallback regex: {e}")

        if self.on_fallback:
            self.on_fallback("Nettoyage : mode regex (LLM indisponible)")
        return self._clean_verbatim(result)

    @staticmethod
    def _clean_verbatim(text: str) -> str:
        """Nettoyage minimal : majuscule + point final, rien d'autre.

        Args:
            text: Texte brut.

        Returns:
            Texte avec ponctuation minimale.
        """
        result = text.strip()
        result = re.sub(r"\s{2,}", " ", result)
        if result and result[0].islower():
            result = result[0].upper() + result[1:]
        if result and result[-1] not in ".!?":
            result += "."
        return result
