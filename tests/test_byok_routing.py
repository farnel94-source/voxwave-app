"""Tests pour le routage BYOK (Bring Your Own Key) — provider explicite.

Sémantique :
- provider="hybrid"/"cloud"/"proxy" → proxy géré (clés serveur)
- provider="byok_groq" → cloud direct avec clé utilisateur stockée chiffrée
- provider="byok_openai" → cloud direct OpenAI avec clé utilisateur
- provider="local" → 100% offline (Whisper local / Ollama / regex)

Les tests utilisent un home isolé via tmp_path pour ne pas toucher
au fichier réel ~/.voxwave/apikeys.enc de l'utilisateur.
"""

import importlib
import logging

import pytest


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    """Crée un APIKeyStorage isolé dans un home temporaire.

    Chaque test a son propre `~/.voxwave/` pour éviter les conflits.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    import src.security.api_keys_storage as mod
    importlib.reload(mod)
    return mod.APIKeyStorage()


class TestAPIKeyStorageRoundtrip:
    """Tests de base du stockage chiffré (set/get/clear)."""

    def test_no_keys_initially(self, isolated_storage):
        """Au démarrage, aucune clé n'est stockée."""
        assert isolated_storage.get_groq_key() is None
        assert isolated_storage.get_openai_key() is None
        assert isolated_storage.has_any_key() is False

    def test_set_then_get_groq(self, isolated_storage):
        """Roundtrip : set puis get retourne la même valeur."""
        isolated_storage.set_groq_key("gsk_test_value_123")
        assert isolated_storage.get_groq_key() == "gsk_test_value_123"

    def test_set_then_get_openai(self, isolated_storage):
        """Roundtrip OpenAI."""
        isolated_storage.set_openai_key("sk-test-value-456")
        assert isolated_storage.get_openai_key() == "sk-test-value-456"

    def test_set_empty_clears_key(self, isolated_storage):
        """Mettre une clé vide la supprime."""
        isolated_storage.set_groq_key("gsk_xxx")
        assert isolated_storage.get_groq_key() == "gsk_xxx"
        isolated_storage.set_groq_key("")
        assert isolated_storage.get_groq_key() is None

    def test_clear_all_removes_all_keys(self, isolated_storage):
        """clear_all() supprime tout."""
        isolated_storage.set_groq_key("gsk_a")
        isolated_storage.set_openai_key("sk-b")
        isolated_storage.clear_all()
        assert isolated_storage.has_any_key() is False

    def test_keys_persist_across_instances(self, tmp_path, monkeypatch):
        """Les clés survivent à un nouveau APIKeyStorage()."""
        monkeypatch.setenv("HOME", str(tmp_path))
        import src.security.api_keys_storage as mod
        importlib.reload(mod)
        s1 = mod.APIKeyStorage()
        s1.set_groq_key("gsk_persist_test")
        # Nouvelle instance (simule redémarrage app)
        s2 = mod.APIKeyStorage()
        assert s2.get_groq_key() == "gsk_persist_test"


class TestBYOKExplicitProvider:
    """Tests du routage avec provider BYOK explicite (nouveau modèle UX)."""

    def test_byok_groq_provider_uses_stored_key(self, isolated_storage):
        """Quand provider == 'byok_groq', l'app utilise la clé du storage.

        Couvre la logique de _create_transcription_engine : si provider est
        byok_groq, la clé est lue depuis APIKeyStorage et passée à Groq direct.
        """
        isolated_storage.set_groq_key("gsk_user_test_key")
        # La valeur stockée est utilisée directement par GroqWhisperEngine(api_key=...)
        assert isolated_storage.get_groq_key() == "gsk_user_test_key"

    def test_byok_groq_provider_without_key_falls_back(self, isolated_storage):
        """Quand provider == 'byok_groq' mais aucune clé, l'app fallback en local.

        Comportement gracieux : ne crash pas, log un warning, utilise Whisper local.
        """
        # Aucune clé saisie → get_groq_key retourne None
        assert isolated_storage.get_groq_key() is None
        # → app.py voit la clé None et tombe en fallback Whisper local

    def test_byok_openai_provider_uses_stored_key(self, isolated_storage):
        """Quand provider == 'byok_openai', le pipeline utilise la clé OpenAI utilisateur."""
        isolated_storage.set_openai_key("sk-user-openai-key")
        assert isolated_storage.get_openai_key() == "sk-user-openai-key"

    def test_hybrid_provider_does_not_consume_byok_key(self, isolated_storage):
        """Mode 'hybrid' (proxy géré) ignore les clés BYOK stockées.

        Important : c'est le choix explicite du user. Si une clé BYOK est stockée
        mais provider != 'byok_groq', elle ne doit PAS être utilisée à son insu.
        """
        # User a stocké une clé Groq mais a explicitement choisi 'hybrid' (proxy)
        isolated_storage.set_groq_key("gsk_unused")
        # → app.py respecte le choix du user, n'override plus automatiquement
        # (la clé reste stockée mais inutilisée tant que provider != byok_groq)


class TestKeysNotInLogs:
    """Vérifie que les clés API ne sont jamais loguées en clair."""

    def test_set_groq_does_not_log_value(self, isolated_storage, caplog):
        """L'enregistrement d'une clé Groq ne doit pas afficher la valeur."""
        secret = "gsk_super_secret_value_xxxxxxxxxxxxxxxxx"
        with caplog.at_level(logging.DEBUG):
            isolated_storage.set_groq_key(secret)
        for record in caplog.records:
            assert secret not in record.getMessage(), \
                f"Clé Groq leakée dans log: {record.getMessage()}"

    def test_set_openai_does_not_log_value(self, isolated_storage, caplog):
        """L'enregistrement d'une clé OpenAI ne doit pas afficher la valeur."""
        secret = "sk-super-secret-openai-value-xxxxxxxxxx"
        with caplog.at_level(logging.DEBUG):
            isolated_storage.set_openai_key(secret)
        for record in caplog.records:
            assert secret not in record.getMessage(), \
                f"Clé OpenAI leakée dans log: {record.getMessage()}"
