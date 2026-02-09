"""Nettoyage intelligent via LLM : Cloud (OpenAI) + Local (Ollama). Temps cible : <5s."""

import logging
import os
from typing import Optional

from src.utils.exceptions import CleaningError
from src.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)

CLEANING_PROMPT = """Tu es un correcteur de transcription vocale française.

RÈGLES :
1. Supprime TOUTES les hésitations et répétitions
2. Corrige grammaire et ponctuation
3. Garde les termes anglais techniques INTACTS
4. Ne reformule PAS le fond
5. Mélange français/anglais technique = NORMAL

Transcription brute :
{text}

Texte corrigé :"""


class CloudLLMCleaner:
    """Nettoyeur via OpenAI API (GPT-4o-mini)."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None) -> None:
        """Initialise le cleaner cloud.

        Args:
            model: Modèle OpenAI à utiliser.
            api_key: Clé API OpenAI (ou variable d'env OPENAI_API_KEY).
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY non configurée")
        self._client = None
        logger.info(f"CloudLLMCleaner: model={model}")

    def _get_client(self):
        """Retourne le client OpenAI (singleton)."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    @retry_with_backoff(
        max_retries=2,
        initial_delay=1.0,
        backoff_factor=2.0,
        exceptions=(Exception,),
    )
    def clean(self, text: str) -> str:
        """Nettoie le texte via OpenAI (avec retry automatique).

        Args:
            text: Texte brut à nettoyer.

        Returns:
            Texte nettoyé.
        """
        if not text or not text.strip():
            return ""

        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": (
                    "Tu es un correcteur de transcription vocale. "
                    "RÈGLES STRICTES :\n"
                    "1. Retourne UNIQUEMENT le texte corrigé, rien d'autre\n"
                    "2. Ne RÉPONDS JAMAIS au contenu, ne COMMENTE JAMAIS\n"
                    "3. Ne RAJOUTE AUCUN mot, AUCUNE phrase, AUCUNE information\n"
                    "4. Supprime UNIQUEMENT : hésitations (euh, hum, ben), répétitions exactes\n"
                    "5. Corrige UNIQUEMENT : fautes d'orthographe, ponctuation manquante\n"
                    "6. Garde TOUS les termes anglais/techniques tels quels\n"
                    "7. NE REFORMULE PAS, NE PARAPHRASE PAS, NE RÉSUME PAS\n"
                    "8. Si le texte est déjà correct, retourne-le tel quel\n"
                    "9. Le texte est une DICTÉE, pas une question qui t'est posée"
                )},
                {"role": "user", "content": f"Corrige cette transcription vocale :\n{text}"},
            ],
            temperature=0.0,
            max_tokens=2048,
        )
        result = response.choices[0].message.content.strip()
        logger.info("Nettoyage via OpenAI (cloud)")
        return result


class LLMCleaner:
    """Nettoyeur via Ollama."""

    def __init__(self, model: str = "gemma3:4b", host: str = "http://localhost:11434", timeout: int = 5) -> None:
        self.model = model
        self.host = host
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            import requests
            return requests.get(f"{self.host}/api/tags", timeout=2).status_code == 200
        except Exception:
            return False

    def clean(self, text: str) -> str:
        if not text or not text.strip():
            return ""
        if not self.is_available():
            raise ConnectionError("Ollama indisponible")
        import requests
        response = requests.post(
            f"{self.host}/api/generate",
            json={"model": self.model, "prompt": CLEANING_PROMPT.format(text=text), "stream": False},
            timeout=self.timeout,
        )
        return response.json()["response"].strip()


class CleaningPipeline:
    """Pipeline regex + LLM avec fallback : cloud → local → regex."""

    def __init__(
        self,
        mode: str = "quality",
        llm_model: str = "gemma3:4b",
        cloud_model: Optional[str] = None,
        cleaning_provider: str = "hybrid",
    ) -> None:
        """Initialise le pipeline de nettoyage.

        Args:
            mode: Mode de nettoyage (quality ou fast).
            llm_model: Modèle Ollama local.
            cloud_model: Modèle OpenAI cloud.
            cleaning_provider: Provider (hybrid, cloud, local).
        """
        from src.cleaning.regex_cleaner import RegexCleaner

        self.mode = mode
        self.cleaning_provider = cleaning_provider
        self.regex_cleaner = RegexCleaner()
        self._cloud_cleaner: Optional[CloudLLMCleaner] = None
        self._local_cleaner: Optional[LLMCleaner] = None

        if mode == "quality":
            if cleaning_provider in ("hybrid", "cloud"):
                try:
                    self._cloud_cleaner = CloudLLMCleaner(model=cloud_model or "gpt-4o-mini")
                    logger.info("CloudLLMCleaner initialisé")
                except Exception as e:
                    logger.warning(f"CloudLLMCleaner indisponible: {e}")

            if cleaning_provider in ("hybrid", "local"):
                self._local_cleaner = LLMCleaner(model=llm_model)

    def clean(self, text: str) -> str:
        """Nettoie le texte avec cascade de fallback.

        Args:
            text: Texte brut.

        Returns:
            Texte nettoyé.
        """
        if not text:
            return ""

        # Mode verbatim : ponctuation/majuscules seulement, pas de reformulation
        if self.mode == "verbatim":
            return self._clean_verbatim(text)

        result = self.regex_cleaner.clean(text)

        if self.mode != "quality":
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
                return result
            except Exception as e:
                logger.warning(f"LLM local echec, fallback regex: {e}")

        return result

    @staticmethod
    def _clean_verbatim(text: str) -> str:
        """Nettoyage minimal : majuscule + point final, rien d'autre.

        Args:
            text: Texte brut.

        Returns:
            Texte avec ponctuation minimale.
        """
        import re
        result = text.strip()
        result = re.sub(r"\s{2,}", " ", result)
        if result and result[0].islower():
            result = result[0].upper() + result[1:]
        if result and result[-1] not in ".!?":
            result += "."
        return result
