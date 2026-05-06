"""Reproduit le bug 'Proxy HTTP 422: x-app-token missing' en dev.

En dev (non frozen), `load_config()` lit `config.yaml` à la racine du projet.
Ce fichier ne contient PAS de `proxy_app_token` (gitignored, le vrai token
vit dans `config.production.yaml`).

Résultat actuel : `proxy_app_token = ""` → ProxyLLMCleaner sans header
→ backend renvoie 422 → warning "Proxy streaming fallback".

Comportement attendu : si `config.production.yaml` existe à côté de
`config.yaml`, ses clés sont mergées par-dessus. Le token est alors
chargé en dev de la même façon qu'en prod.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import yaml


def test_load_config_merges_production_yaml_in_dev(tmp_path, monkeypatch):
    """En dev, load_config doit fusionner config.production.yaml par-dessus config.yaml."""
    # Setup : faux projet dev avec les deux fichiers
    config_yaml = tmp_path / "config.yaml"
    config_prod = tmp_path / "config.production.yaml"

    config_yaml.write_text(yaml.safe_dump({
        "transcription": {"provider": "hybrid", "proxy_url": "https://example.com"},
        "cleaning": {"provider": "hybrid", "proxy_url": "https://example.com",
                     "mode": "quality", "llm_model": "gemma3:4b"},
    }))
    # Format réel : clé flat à la racine (comme dans le vrai config.production.yaml,
    # cf. build.py:_inject_production_secrets qui lit `secrets.get("proxy_app_token")`)
    config_prod.write_text(yaml.safe_dump({"proxy_app_token": "TOKEN_DEV_123"}))

    # Force user_config_path à pointer vers le tmp config.yaml
    from src.utils import platform as platform_mod
    monkeypatch.setattr(platform_mod, "user_config_path",
                        lambda: str(config_yaml))
    monkeypatch.setattr("src.app.user_config_path",
                        lambda: str(config_yaml), raising=False)

    from src.app import load_config
    config = load_config(str(config_yaml))

    assert config["transcription"]["proxy_app_token"] == "TOKEN_DEV_123", \
        "load_config doit charger le token depuis config.production.yaml en dev"
    assert config["cleaning"]["proxy_app_token"] == "TOKEN_DEV_123", \
        "Idem côté cleaning"
