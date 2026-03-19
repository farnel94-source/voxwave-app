"""Tests qui prouvent les 3 bugs de la session 2.

Ces tests ÉCHOUENT avant le fix et PASSENT après.
"""

import inspect


class TestBug1_SileroVADUrl:
    """Bug 1 : silero_vad.py sur Windows a la vieille URL (404).

    La bonne URL est /master/src/silero_vad/data/silero_vad.onnx
    L'ancienne URL est /raw/master/files/silero_vad.onnx (404)
    """

    def test_silero_url_does_not_use_old_files_path(self):
        """BUG CONFIRMÉ si l'URL pointe encore vers /files/silero_vad.onnx."""
        from src.audio.silero_vad import _MODEL_URL

        assert "files/silero_vad.onnx" not in _MODEL_URL, (
            f"BUG : URL obsolète '{_MODEL_URL}' — "
            "ce chemin n'existe plus dans le repo Silero v5"
        )

    def test_silero_url_points_to_correct_v5_path(self):
        """Vérifie que l'URL pointe vers le chemin v5 correct."""
        from src.audio.silero_vad import _MODEL_URL

        assert "src/silero_vad/data/silero_vad.onnx" in _MODEL_URL, (
            f"URL actuelle : '{_MODEL_URL}' — "
            "doit pointer vers src/silero_vad/data/silero_vad.onnx (chemin v5)"
        )


class TestBug2_CodeProfileCallsOllama:
    """Bug 2 : profil 'code' appelle pipeline.clean() qui tente Ollama.

    Comportement actuel (bug) :
        app_profile == "code" → self.pipeline.clean(raw_text)
        CleaningPipeline.clean() → regex → cloud → OLLAMA → verbatim

    Comportement attendu (après fix) :
        app_profile == "code" → regex uniquement, JAMAIS Ollama
    """

    def test_code_profile_does_not_call_full_pipeline(self):
        """BUG CONFIRMÉ si app.py appelle self.pipeline.clean() pour le profil code.

        self.pipeline.clean() inclut l'appel Ollama dans la cascade.
        Le fix correct : appeler le regex cleaner directement.
        """
        import src.app as app_module

        # Lire le source de la méthode qui gère le pipeline
        source = inspect.getsource(app_module)

        # Chercher le bloc code profile
        code_profile_idx = source.find("'code' → verbatim")
        assert code_profile_idx != -1, "Le log 'code → verbatim' est introuvable dans app.py"

        # Extraire ~300 chars autour du log pour voir ce qui est appelé
        snippet = source[code_profile_idx: code_profile_idx + 300]

        # Dans le bug, pipeline.clean() est appelé directement après le log
        # Après fix, il ne doit PAS y avoir pipeline.clean() dans ce bloc
        assert "pipeline.clean(" not in snippet, (
            "BUG CONFIRMÉ : app.py appelle self.pipeline.clean() pour le profil 'code'. "
            "pipeline.clean() tente Ollama dans sa cascade. "
            "Fix attendu : utiliser regex_cleaner directement."
        )

    def test_cleaning_pipeline_clean_calls_local_cleaner_when_cloud_unavailable(self):
        """Prouve que CleaningPipeline.clean() appelle bien Ollama (local_cleaner).

        Ce test documente que le code profile, en appelant pipeline.clean(),
        déclenche l'appel Ollama — même si on veut juste du regex.
        """
        from unittest.mock import MagicMock, patch
        from src.cleaning.llm_cleaner import CleaningPipeline

        pipeline = CleaningPipeline(mode="auto", cleaning_provider="local")

        call_count = 0

        def mock_local_clean(text, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Ollama down")

        pipeline._local_cleaner = MagicMock()
        pipeline._local_cleaner.clean.side_effect = mock_local_clean

        # cloud absent → pipeline devrait tomber sur Ollama
        pipeline._cloud_cleaner = None

        pipeline.clean("test texte")

        assert call_count == 1, (
            f"BUG CONFIRMÉ : pipeline.clean() a appelé Ollama {call_count} fois. "
            "Le profil 'code' ne devrait jamais appeler Ollama."
        )


class TestBug3_OllamaConnectTimeoutTooLong:
    """Bug 3 : connect_timeout Ollama (5s) > seuil progressive_injector (5.0s).

    Quand Ollama est absent, la connexion refuse après ~5s.
    Le progressive injector rejette le remplacement après 5.0s.
    Résultat : le texte brut n'est jamais remplacé.

    Fix : réduire le connect_timeout à ≤ 1s.
    """

    def test_ollama_connect_timeout_fits_within_progressive_injector_threshold(self):
        """BUG CONFIRMÉ si le connect_timeout est > 1.0s.

        Le seuil du progressive injector est 5.0s.
        Avec un connect_timeout de 5s, Ollama consomme tout le budget.
        """
        import ast
        from pathlib import Path

        source = Path("src/cleaning/llm_cleaner.py").read_text()
        # Chercher timeout=(X, Y) dans LLMCleaner.clean
        # Le connect_timeout est le premier élément du tuple
        idx = source.find("timeout=(")
        assert idx != -1, "timeout= introuvable dans llm_cleaner.py"

        snippet = source[idx: idx + 30]  # ex: "timeout=(5, self.timeout)"
        # Extraire le premier chiffre du tuple
        import re
        m = re.search(r"timeout=\((\d+)", snippet)
        assert m, f"Format timeout non reconnu : {snippet}"
        connect_timeout = int(m.group(1))

        assert connect_timeout <= 1, (
            f"BUG CONFIRMÉ : connect_timeout={connect_timeout}s trop long. "
            f"Le progressive injector rejette après 5.0s. "
            f"Fix attendu : connect_timeout ≤ 1s pour localhost."
        )
