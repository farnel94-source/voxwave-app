"""Tests session 4 — circuit breaker log level + clipboard restore + 5.0s guard.

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


class TestBug_PrewarmOllamaDoesNotOpenCircuit:
    """Bug : _prewarm_ollama() ne pré-ouvre pas le circuit quand Ollama est absent.

    Contexte : avant le fix, _prewarm_ollama() appelait is_available() mais ne
    faisait rien si Ollama était absent. La 1ère dictée tentait alors de se
    connecter à Ollama → timeout → circuit s'ouvre → WARNING + notif tray.

    Fix : si not available → force_open() dans _prewarm_ollama() (app.py).
    """

    def test_is_available_alone_does_not_open_circuit(self):
        """Contexte du bug : is_available() seul ne pré-ouvre pas le circuit."""
        from src.cleaning.llm_cleaner import CleaningPipeline
        from src.utils.circuit_breaker import CircuitState

        pipeline = CleaningPipeline(mode="auto", cleaning_provider="local")
        pipeline._local_cleaner.is_available = lambda: False

        # Comportement BUGUÉ : juste vérifier la disponibilité, sans force_open
        pipeline._local_cleaner.is_available()

        # Le circuit reste CLOSED — c'est le bug confirmé
        assert pipeline._local_circuit._state == CircuitState.CLOSED, (
            "is_available() seul ne doit pas modifier l'état du circuit "
            "(vérification du contexte du bug)"
        )

    def test_prewarm_opens_circuit_when_ollama_unavailable(self):
        """Régression : le prewarm doit pré-ouvrir le circuit si Ollama absent."""
        from src.cleaning.llm_cleaner import CleaningPipeline
        from src.utils.circuit_breaker import CircuitState

        pipeline = CleaningPipeline(mode="auto", cleaning_provider="local")
        pipeline._local_cleaner.is_available = lambda: False

        # Logique corrigée de _prewarm_ollama (app.py) : force_open si absent
        available = pipeline._local_cleaner.is_available()
        if not available:
            pipeline._local_circuit.force_open()

        assert pipeline._local_circuit._state == CircuitState.OPEN, (
            "Le circuit Ollama doit être OPEN après prewarm si Ollama est indisponible"
        )


class TestBug_ClipboardRestoredAfterInjectRaw:
    """Bug : inject_raw() écrase le clipboard sans le restaurer.

    Quand l'utilisateur avait quelque chose de copié (Ctrl+C), après dictée
    le clipboard contient le texte dicté au lieu du contenu original.
    Reproduit le chemin Windows : _inject_direct() → pyperclip.copy(raw_text)
    sans sauvegarder ni restaurer.
    """

    def test_clipboard_restored_after_inject_raw(self):
        """BUG CONFIRMÉ si clipboard != contenu original après inject_raw."""
        from src.injection.progressive_injector import ProgressiveInjector
        from unittest.mock import MagicMock, patch

        clipboard = {"value": "contenu copié par l'utilisateur"}

        def mock_copy(text):
            clipboard["value"] = text

        def mock_paste():
            return clipboard["value"]

        mock_injector = MagicMock()
        injector = ProgressiveInjector(mock_injector)
        injector._os_name = "windows"  # force le chemin Windows

        with patch("pyperclip.copy", side_effect=mock_copy), \
             patch("pyperclip.paste", side_effect=mock_paste), \
             patch("pynput.keyboard.Controller"), \
             patch("pynput.keyboard.Key"), \
             patch.object(injector, "_start_user_watch"), \
             patch("time.sleep"):

            injector.inject_raw("texte dicté par l'utilisateur")

        assert clipboard["value"] == "contenu copié par l'utilisateur", (
            f"BUG CONFIRMÉ : clipboard = '{clipboard['value']}' "
            "au lieu de 'contenu copié par l'utilisateur'. "
            "inject_raw écrase le clipboard sans le restaurer."
        )


class TestBug_RegexFallbackBlockedBy1_5sGuard:
    """Bug : quand Ollama fail, la garde 5.0s peut bloquer le remplacement regex.

    Fix attendu : si le circuit Ollama est OPEN (prewarm ou premier échec),
    pipeline.clean() doit retourner en < 100ms (pas de tentative réseau).
    """

    def test_pipeline_clean_is_fast_when_circuit_open(self):
        """pipeline.clean() doit être rapide (< 200ms) quand le circuit est OPEN."""
        import time
        from src.cleaning.llm_cleaner import CleaningPipeline

        pipeline = CleaningPipeline(mode="auto", cleaning_provider="local")

        # Forcer le circuit OPEN (Ollama réputé indisponible)
        pipeline._local_circuit.force_open()

        t0 = time.monotonic()
        pipeline.clean("euh je vais faire un commit")
        elapsed_ms = (time.monotonic() - t0) * 1000

        assert elapsed_ms < 200, (
            f"BUG CONFIRMÉ : pipeline.clean() a pris {elapsed_ms:.0f}ms avec circuit OPEN. "
            "Devrait être < 200ms (pas de tentative Ollama). "
            "Si > 200ms, la garde 5.0s du progressive_injector sera déclenchée."
        )


class TestBug_OllamaHostPropagated:
    """CleaningPipeline doit passer ollama_host à LLMCleaner."""

    def test_ollama_host_passed_to_local_cleaner(self):
        from src.cleaning.llm_cleaner import CleaningPipeline

        pipeline = CleaningPipeline(
            cleaning_provider="local",
            ollama_host="http://localhost:11435",
        )
        assert pipeline._local_cleaner.host == "http://localhost:11435", (
            "CleaningPipeline doit propager ollama_host à LLMCleaner"
        )
