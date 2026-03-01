"""Tests qui prouvent les 2 bugs identifiés dans llm_cleaner.py.

Ces tests sont VOLONTAIREMENT ÉCRITS POUR ÉCHOUER — ils valident la présence des bugs.
Ils passeront une fois les bugs corrigés.
"""

import inspect


class TestBug1_OllamaTimeout:
    """Bug 1 : is_available() appelé à chaque clean() + timeout trop court.

    Problèmes :
    - is_available() fait un appel HTTP GET à chaque clean() → latence +2s si down
    - read_timeout=5s trop court pour gemma3:4b sur CPU (peut prendre 15-30s)
    """

    def test_is_available_called_every_clean_is_inefficient(self):
        """DOIT ÉCHOUER : is_available() est appelé à chaque clean(), pas mis en cache.

        Comportement attendu (après fix) : is_available() n'est appelé qu'une fois
        au démarrage, pas à chaque appel de clean().
        """
        from src.cleaning.llm_cleaner import LLMCleaner

        cleaner = LLMCleaner(host="http://localhost:11434")
        call_count = 0

        def counting_is_available():
            nonlocal call_count
            call_count += 1
            return False  # Simule Ollama indisponible

        cleaner.is_available = counting_is_available

        # 3 appels à clean()
        for _ in range(3):
            try:
                cleaner.clean("texte de test")
            except Exception:
                pass

        # DOIT ÉCHOUER : is_available() est appelé 3 fois (une par clean())
        # Après fix : devrait être appelé 0 fois en cours de session (flag _available)
        assert call_count == 0, (
            f"BUG CONFIRMÉ : is_available() a été appelé {call_count} fois "
            f"(attendu 0 — devrait utiliser un flag _available mis en cache)"
        )

    def test_read_timeout_is_sufficient_for_slow_cpu(self):
        """Vérifie que le timeout PAR DÉFAUT est suffisant pour gemma3:4b sur CPU lent.

        Fix appliqué : timeout par défaut = 30s (était 5s).
        gemma3:4b peut prendre 15-30s sur CPU sans GPU.
        """
        from src.cleaning.llm_cleaner import LLMCleaner

        # Timeout par défaut (sans argument) — c'est ça qui compte
        cleaner = LLMCleaner()

        assert cleaner.timeout >= 30, (
            f"read_timeout={cleaner.timeout}s trop court pour CPU lent. "
            f"Minimum recommandé : 30s pour gemma3:4b"
        )


class TestBug2_OllamaLanguagePreservation:
    """Bug 2 : CLEANING_PROMPT (Ollama) n'a pas d'exemples multilingues.

    Problème : Ollama utilise CLEANING_PROMPT (anglais, sans exemples) alors
    qu'OpenAI utilise _SYSTEM_PROMPT (avec exemples FR, EN, DE, ES).
    Résultat : gemma3:4b répond en anglais même si l'input est en français.
    """

    def test_system_prompt_used_by_ollama_contains_french_example(self):
        """Vérifie que _SYSTEM_PROMPT (maintenant utilisé par Ollama) a des exemples FR.

        Fix appliqué : LLMCleaner.clean() utilise désormais _SYSTEM_PROMPT
        (avec exemples EN, FR, DE, ES) via /api/chat.
        """
        from src.cleaning.llm_cleaner import _SYSTEM_PROMPT

        # Le prompt utilisé par Ollama doit avoir des exemples français
        has_french_example = (
            "euh" in _SYSTEM_PROMPT.lower()
            or "french" in _SYSTEM_PROMPT.lower()
            or "français" in _SYSTEM_PROMPT.lower()
        )

        assert has_french_example, (
            "_SYSTEM_PROMPT n'a pas d'exemple français. "
            "gemma3:4b risque de répondre en anglais."
        )

    def test_ollama_uses_chat_api_not_generate(self):
        """DOIT ÉCHOUER : LLMCleaner utilise /api/generate au lieu de /api/chat.

        /api/chat supporte un system prompt séparé (meilleure instruction following).
        /api/generate mélange tout dans un seul texte.
        """
        from src.cleaning.llm_cleaner import LLMCleaner

        source = inspect.getsource(LLMCleaner.clean)

        assert "/api/chat" in source, (
            "BUG CONFIRMÉ : LLMCleaner.clean() utilise /api/generate au lieu de "
            "/api/chat. L'endpoint /api/chat supporte le system prompt séparé, "
            "ce qui est crucial pour la preservation de langue avec gemma3:4b."
        )

    def test_ollama_prompt_uses_system_prompt_with_multilingual_examples(self):
        """DOIT ÉCHOUER : Ollama n'utilise pas _SYSTEM_PROMPT (avec exemples multilingues).

        CloudLLMCleaner utilise _SYSTEM_PROMPT (FR+EN+DE+ES).
        LLMCleaner utilise CLEANING_PROMPT (anglais simple, pas d'exemples).
        Ce test vérifie que les deux utilisent le même prompt de qualité.
        """
        from src.cleaning.llm_cleaner import LLMCleaner

        source = inspect.getsource(LLMCleaner.clean)

        assert "_SYSTEM_PROMPT" in source, (
            "BUG CONFIRMÉ : LLMCleaner.clean() n'utilise pas _SYSTEM_PROMPT. "
            "Il utilise CLEANING_PROMPT (ancien prompt sans exemples multilingues). "
            "Attendu : utiliser _SYSTEM_PROMPT comme CloudLLMCleaner, "
            "avec les exemples EN, FR, DE, ES."
        )

    def test_validate_output_language_mismatch_known_limitation(self):
        """LIMITATION CONNUE : _validate_output ne détecte pas les changements de langue.

        _validate_output vérifie le ratio de longueur et les marqueurs de reformulation,
        mais pas la cohérence de langue (nécessiterait langdetect ou similaire).
        La vraie protection est dans le prompt : _SYSTEM_PROMPT interdit la traduction.
        Ce test documente la limitation sans bloquer la suite.
        """
        from src.cleaning.llm_cleaner import _validate_output

        french_input = "euh je vais faire un commit sur la branche main quoi"
        english_output = "I'm going to make a commit on the main branch."

        # _validate_output retourne True (ratio correct, pas de marqueur de reformulation)
        # La protection langue est dans le prompt, pas dans la validation
        result = _validate_output(french_input, english_output)
        # Limitation documentée : True est attendu (pas de détection langue)
        assert result is True, (
            "La validation de ratio a changé — vérifier _validate_output."
        )
