"""Décorateur retry avec backoff exponentiel."""

import functools
import logging
import time
from typing import Tuple, Type

logger = logging.getLogger(__name__)


def _is_network_error(exc: Exception) -> bool:
    """Detecte si une exception est une erreur reseau (timeout, connexion).

    Args:
        exc: Exception a analyser.

    Returns:
        True si c'est une erreur reseau.
    """
    # Exceptions Python standard
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True

    # httpx (utilise par Groq SDK et OpenAI SDK)
    exc_name = type(exc).__name__
    if exc_name in ("ConnectError", "ConnectTimeout", "ReadTimeout", "TimeoutException"):
        return True

    # Verifier la cause chainee
    if exc.__cause__ and _is_network_error(exc.__cause__):
        return True

    return False


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    network_retries: int = 0,
):
    """Décorateur retry avec backoff exponentiel.

    Args:
        max_retries: Nombre maximum de tentatives.
        initial_delay: Délai initial en secondes.
        backoff_factor: Facteur multiplicatif du délai.
        exceptions: Tuple d'exceptions à intercepter.
        network_retries: Nombre de retries pour les erreurs reseau (0 = pas de retry).

    Returns:
        Décorateur.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    # Erreur reseau : abandonner vite (pas de retry ou retries limites)
                    if _is_network_error(e) and attempt >= network_retries:
                        logger.warning(
                            f"{func.__name__} erreur réseau, abandon immédiat: {e}"
                        )
                        raise

                    if attempt < max_retries - 1:
                        logger.warning(
                            f"{func.__name__} tentative {attempt + 1}/{max_retries} "
                            f"échouée: {e}. Retry dans {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"{func.__name__} échoué après {max_retries} tentatives: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator
