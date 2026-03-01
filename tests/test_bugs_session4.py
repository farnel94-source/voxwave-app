"""Tests session 4 — circuit breaker log level.

Le circuit breaker fonctionne (pas de connexion TCP) mais log WARNING à tort.
"""

import logging
from unittest.mock import MagicMock, patch
import requests as requests_lib


class TestBug_CircuitBreakerLogsWarning:
    """Bug : CleaningPipeline logue WARNING même quand le circuit est ouvert.

    Le circuit ouvert = comportement normal (Ollama absent).
    Ça ne doit PAS être loggé WARNING — seulement DEBUG.
    """

    def test_circuit_open_does_not_log_warning(self, caplog):
        """BUG CONFIRMÉ si un WARNING apparaît quand le circuit est ouvert."""
        from src.cleaning.llm_cleaner import CleaningPipeline

        pipeline = CleaningPipeline(mode="auto", cleaning_provider="local")

        # Forcer le circuit en état OPEN (simule 1 échec réseau précédent)
        pipeline._local_circuit.force_open()

        with caplog.at_level(logging.WARNING, logger="src.cleaning.llm_cleaner"):
            pipeline.clean("bonjour monde")

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING
                    and "circuit" in r.message.lower()]

        assert len(warnings) == 0, (
            f"BUG CONFIRMÉ : {len(warnings)} WARNING(s) loggé(s) alors que le "
            "circuit est ouvert (comportement normal). "
            f"Message : '{warnings[0].message if warnings else ''}'"
        )

    def test_real_failure_still_logs_warning(self, caplog):
        """Vérifie que les vraies erreurs réseau sont encore loggées WARNING."""
        from src.cleaning.llm_cleaner import CleaningPipeline

        pipeline = CleaningPipeline(mode="auto", cleaning_provider="local")

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests_lib.exceptions.ConnectionError("Refused")

            with caplog.at_level(logging.WARNING, logger="src.cleaning.llm_cleaner"):
                pipeline.clean("bonjour monde")

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING
                    and "echec" in r.message.lower()]

        assert len(warnings) >= 1, (
            "Le premier échec réseau réel doit toujours être loggé WARNING."
        )
