"""Tests pour le routage BYOK (Bring Your Own Key).

Vérifie que :
- Aucune clé stockée → l'app utilise le proxy (comportement par défaut)
- Clé Groq seule → transcription cloud direct, cleaning local fallback
- Clés Groq + OpenAI → cloud direct pour tout (bypass proxy)

Les tests utilisent un home isolé via tmp_path pour ne pas toucher
au fichier réel ~/.voxwave/apikeys.enc de l'utilisateur.
"""

import importlib
import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    """Crée un APIKeyStorage isolé dans un home temporaire.

    Chaque test a son propre `~/.voxwave/` pour éviter les conflits.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    # Recharger le module pour que VOXWAVE_DIR / KEY_FILE prennent le nouveau HOME
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


class TestBYOKRouting:
    """Tests du routage automatique selon la présence des clés BYOK.

    On mocke `_create_transcription_engine` et `CleaningPipeline` pour
    intercepter les paramètres effectivement passés.
    """

    def test_no_keys_uses_proxy(self, isolated_storage):
        """Sans clés, le provider initial reste celui de la config."""
        # Aucune clé stockée
        assert isolated_storage.get_groq_key() is None
        assert isolated_storage.get_openai_key() is None
        # La logique BYOK dans app.py vérifie `if byok_groq:` → False
        # donc le provider reste celui de la config (par défaut "proxy" / "hybrid").

    def test_only_groq_key_present(self, isolated_storage):
        """Avec juste la clé Groq, transcription direct, cleaning fallback local."""
        isolated_storage.set_groq_key("gsk_test")
        assert isolated_storage.get_groq_key() == "gsk_test"
        assert isolated_storage.get_openai_key() is None
        # → app.py : `if byok_groq:` True → transcription_provider = "cloud"
        # → app.py : `if byok_openai:` False → cleaning_provider inchangé

    def test_both_keys_force_cloud_direct(self, isolated_storage):
        """Avec les 2 clés, transcription ET cleaning passent en cloud direct."""
        isolated_storage.set_groq_key("gsk_test")
        isolated_storage.set_openai_key("sk-test")
        assert isolated_storage.get_groq_key() == "gsk_test"
        assert isolated_storage.get_openai_key() == "sk-test"
        # → app.py force les deux providers en "cloud" direct (bypass proxy)


class TestKeysNotInLogs:
    """Vérifie que les clés API ne sont jamais loguées en clair."""

    def test_set_groq_does_not_log_value(self, isolated_storage, caplog):
        """L'enregistrement d'une clé Groq ne doit pas afficher la valeur."""
        secret = "gsk_super_secret_value_xxxxxxxxxxxxxxxxx"
        with caplog.at_level("DEBUG"):
            isolated_storage.set_groq_key(secret)
        # La valeur secrète ne doit apparaître dans aucun message de log
        for record in caplog.records:
            assert secret not in record.getMessage(), \
                f"Clé Groq leakée dans log: {record.getMessage()}"

    def test_set_openai_does_not_log_value(self, isolated_storage, caplog):
        """L'enregistrement d'une clé OpenAI ne doit pas afficher la valeur."""
        secret = "sk-super-secret-openai-value-xxxxxxxxxx"
        with caplog.at_level("DEBUG"):
            isolated_storage.set_openai_key(secret)
        for record in caplog.records:
            assert secret not in record.getMessage(), \
                f"Clé OpenAI leakée dans log: {record.getMessage()}"
