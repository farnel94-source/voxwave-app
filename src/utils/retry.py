"""Décorateur retry avec backoff exponentiel."""

import functools
import logging
import time
from typing import Tuple, Type

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Décorateur retry avec backoff exponentiel.

    Args:
        max_retries: Nombre maximum de tentatives.
        initial_delay: Délai initial en secondes.
        backoff_factor: Facteur multiplicatif du délai.
        exceptions: Tuple d'exceptions à intercepter.

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
