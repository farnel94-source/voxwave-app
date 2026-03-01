"""Tests qui prouvent les 2 bugs de la session 3.

Ces tests ÉCHOUENT avant le fix et PASSENT après.
"""

import inspect
import time
from unittest.mock import MagicMock, patch


class TestBug1_NoCircuitBreakerForOllama:
    """Bug 1 : pas de circuit breaker pour Ollama local.

    Résultat : chaque clean() tente une connexion TCP (1-2s sur Windows).
    Le progressive injector (seuil 1.5s) est toujours dépassé.

    Fix attendu :
    - CleaningPipeline crée un _local_circuit (CircuitBreaker)
    - LLMCleaner.clean() vérifie le circuit avant de tenter la connexion
    - Après 1 échec réseau → circuit OPEN → les appels suivants sont instantanés
    """

    def test_cleaning_pipeline_has_local_circuit_breaker(self):
        """BUG CONFIRMÉ si CleaningPipeline n'a pas de _local_circuit."""
        from src.cleaning.llm_cleaner import CleaningPipeline

        pipeline = CleaningPipeline(mode="auto", cleaning_provider="local")

        assert hasattr(pipeline, "_local_circuit"), (
            "BUG CONFIRMÉ : CleaningPipeline n'a pas de '_local_circuit'. "
            "Sans circuit breaker, chaque clean() tente une connexion TCP à Ollama "
            "(1-2s sur Windows à cause du dual-stack IPv6/IPv4)."
        )

    def test_llm_cleaner_has_set_circuit_breaker_method(self):
        """BUG CONFIRMÉ si LLMCleaner n'a pas de set_circuit_breaker()."""
        from src.cleaning.llm_cleaner import LLMCleaner

        cleaner = LLMCleaner()

        assert hasattr(cleaner, "set_circuit_breaker"), (
            "BUG CONFIRMÉ : LLMCleaner n'a pas de méthode set_circuit_breaker(). "
            "Le circuit breaker ne peut pas être attaché."
        )

    def test_second_ollama_call_skips_requests_after_failure(self):
        """BUG CONFIRMÉ si requests.post est appelé 2 fois malgré l'échec.

        Avec circuit breaker : 2e appel → circuit OPEN → requests.post jamais appelé.
        Sans circuit breaker : requests.post appelé à chaque clean() → 1-2s sur Windows.
        """
        import requests as requests_lib
        from src.cleaning.llm_cleaner import CleaningPipeline

        pipeline = CleaningPipeline(mode="auto", cleaning_provider="local")

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests_lib.exceptions.ConnectionError("Refused")

            # 1er appel : échoue, devrait ouvrir le circuit
            pipeline.clean("premier texte")
            assert mock_post.call_count == 1

            # 2e appel : avec circuit breaker, requests.post ne doit PAS être rappelé
            pipeline.clean("deuxième texte")

            assert mock_post.call_count == 1, (
                f"BUG CONFIRMÉ : requests.post a été appelé {mock_post.call_count} fois. "
                "Avec circuit breaker ouvert, le 2e appel doit bypasser requests.post. "
                "Sans circuit breaker, chaque clean() tente une connexion TCP à Ollama."
            )


class TestBug2_NoConfidenceThresholdInWhisper:
    """Bug 2 : pas de seuil de confiance dans WhisperEngine.

    Résultat : Whisper détecte 'it' (0.80), 'en' (0.62), 'de' (0.49)
    quand l'utilisateur parle français → hallucinations pures.

    Fix attendu :
    - Si language_probability < 0.7 et mode auto → utiliser _last_known_language
    - _last_known_language = dernière langue avec confiance ≥ 0.7
    """

    def test_whisper_engine_has_confidence_threshold(self):
        """BUG CONFIRMÉ si whisper_engine.py n'utilise pas language_probability."""
        import src.transcription.whisper_engine as we_module

        source = inspect.getsource(we_module)

        assert "language_probability" in source, (
            "BUG CONFIRMÉ : whisper_engine.py n'utilise pas 'language_probability'. "
            "Sans seuil de confiance, Whisper transcrit dans une langue détectée "
            "avec 0.49 de confiance → hallucinations pures."
        )

    def test_whisper_engine_has_last_known_language(self):
        """BUG CONFIRMÉ si WhisperEngine n'a pas de _last_known_language."""
        from src.transcription.whisper_engine import WhisperEngine

        engine = WhisperEngine(model="base", language="auto")

        assert hasattr(engine, "_last_known_language"), (
            "BUG CONFIRMÉ : WhisperEngine n'a pas de '_last_known_language'. "
            "Sans cette variable, impossible de revenir à la dernière langue connue "
            "quand la confiance de détection est faible."
        )

    def test_low_confidence_detection_falls_back_to_last_known(self):
        """BUG CONFIRMÉ si une confiance 0.49 écrase la dernière langue connue.

        Scénario réel :
        1. Premier appel : 'fr' avec 0.91 → _last_known_language = 'fr'
        2. Deuxième appel : 'de' avec 0.49 → DOIT revenir à 'fr', pas accepter 'de'
        """
        import numpy as np
        from src.transcription.whisper_engine import WhisperEngine

        engine = WhisperEngine(model="base", language="auto")
        engine._model = MagicMock()

        audio = np.zeros(16000, dtype=np.float32)

        # Appel 1 : 'fr' avec confiance 0.91 → mémorisé comme langue connue
        fake_info_fr = MagicMock()
        fake_info_fr.language = "fr"
        fake_info_fr.language_probability = 0.91
        fake_seg = MagicMock()
        fake_seg.text = "bonjour"
        engine._model.transcribe.return_value = ([fake_seg], fake_info_fr)
        engine.transcribe(audio)
        assert engine._last_known_language == "fr"

        # Appel 2 : 'de' avec confiance 0.49 → doit revenir à 'fr'
        fake_info_de = MagicMock()
        fake_info_de.language = "de"
        fake_info_de.language_probability = 0.49
        engine._model.transcribe.return_value = ([fake_seg], fake_info_de)
        engine.transcribe(audio)

        assert engine._last_detected_language == "fr", (
            f"BUG CONFIRMÉ : langue détectée = '{engine._last_detected_language}' "
            "au lieu de 'fr'. La confiance 0.49 devrait être rejetée et "
            "la langue 'fr' précédemment connue devrait être conservée."
        )
