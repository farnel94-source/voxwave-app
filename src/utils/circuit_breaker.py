"""Circuit breaker pour les appels cloud (Groq, OpenAI).

3 etats : CLOSED (normal), OPEN (skip cloud), HALF_OPEN (test 1 requete).
Thread-safe.
"""

import logging
import threading
import time
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Etats du circuit breaker."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker thread-safe pour les appels reseau.

    Args:
        name: Nom du circuit (pour les logs).
        failure_threshold: Nombre d'echecs consecutifs avant ouverture.
        cooldown_seconds: Duree avant de retenter (etat HALF_OPEN).
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """Etat actuel du circuit."""
        with self._lock:
            return self._get_state()

    def _get_state(self) -> CircuitState:
        """Etat interne (doit etre appele sous lock)."""
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            if time.monotonic() - self._last_failure_time >= self.cooldown_seconds:
                self._state = CircuitState.HALF_OPEN
                logger.info(f"CircuitBreaker[{self.name}]: OPEN -> HALF_OPEN (cooldown expire)")
        return self._state

    def should_allow_request(self) -> bool:
        """Verifie si une requete doit etre autorisee.

        Returns:
            True si la requete peut passer.
        """
        with self._lock:
            state = self._get_state()
            if state == CircuitState.CLOSED:
                return True
            if state == CircuitState.HALF_OPEN:
                return True
            # OPEN
            return False

    def record_success(self) -> None:
        """Enregistre un succes (ferme le circuit)."""
        with self._lock:
            if self._state != CircuitState.CLOSED:
                logger.info(f"CircuitBreaker[{self.name}]: {self._state.value} -> CLOSED")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None

    def record_failure(self) -> None:
        """Enregistre un echec (peut ouvrir le circuit)."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"CircuitBreaker[{self.name}]: HALF_OPEN -> OPEN (echec lors du test)"
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"CircuitBreaker[{self.name}]: CLOSED -> OPEN "
                    f"({self._failure_count} echecs consecutifs)"
                )

    def record_network_failure(self) -> None:
        """Enregistre une erreur reseau (ouvre le circuit immediatement).

        Les erreurs reseau (timeout, connexion refusee) indiquent que le
        service est injoignable. Pas besoin d'attendre N echecs.
        """
        with self._lock:
            self._failure_count = self.failure_threshold
            self._last_failure_time = time.monotonic()
            prev = self._state.value
            self._state = CircuitState.OPEN
            logger.warning(
                f"CircuitBreaker[{self.name}]: {prev} -> OPEN (erreur réseau, ouverture immédiate)"
            )

    def force_open(self) -> None:
        """Force l'ouverture du circuit (ex: check connectivite au demarrage)."""
        with self._lock:
            self._state = CircuitState.OPEN
            self._last_failure_time = time.monotonic()
            logger.info(f"CircuitBreaker[{self.name}]: force OPEN")
