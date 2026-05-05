"""Stockage chiffré des clés API utilisateur (BYOK).

Réutilise le pattern Fernet déjà éprouvé dans `src/licensing/storage.py` :
- Clé de chiffrement dans `~/.voxwave/.key` (partagée avec la licence)
- Clés API chiffrées dans `~/.voxwave/apikeys.enc`
- Permissions 0o600 atomiques

Les clés API ne sont JAMAIS loguées en clair, jamais sérialisées ailleurs
qu'à cet endroit. Le getter retourne None si la clé est vide ou absente.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

VOXWAVE_DIR = Path.home() / ".voxwave"
API_KEYS_FILE = VOXWAVE_DIR / "apikeys.enc"
KEY_FILE = VOXWAVE_DIR / ".key"

# Noms internes des champs (clés du dict chiffré)
_FIELD_GROQ = "groq_api_key"
_FIELD_OPENAI = "openai_api_key"


class APIKeyStorage:
    """Lecture et écriture chiffrées des clés API utilisateur (BYOK).

    Toutes les opérations sont thread-safe au niveau filesystem (écriture
    atomique via O_CREAT|O_TRUNC + permissions 0o600 dès la création).

    Example:
        storage = APIKeyStorage()
        storage.set_groq_key("gsk_...")
        key = storage.get_groq_key()
    """

    def __init__(self) -> None:
        VOXWAVE_DIR.mkdir(parents=True, exist_ok=True)
        self._fernet = self._get_or_create_fernet()

    def _get_or_create_fernet(self) -> Fernet:
        """Charge ou génère la clé Fernet locale.

        Réutilise `~/.voxwave/.key` (partagée avec LicenseStorage), ce qui
        permet de gérer plusieurs secrets utilisateur avec la même clé sans
        en démultiplier la surface d'attaque.

        Returns:
            Instance Fernet pour chiffrement/déchiffrement.
        """
        if KEY_FILE.exists():
            key = KEY_FILE.read_bytes()
        else:
            key = Fernet.generate_key()
            fd = os.open(str(KEY_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(key)
        return Fernet(key)

    def _load_all(self) -> Dict[str, str]:
        """Charge le dict complet des clés API (déchiffré).

        Returns:
            Dict avec clés `groq_api_key`, `openai_api_key`. Vide si fichier absent.
        """
        if not API_KEYS_FILE.exists():
            return {}
        try:
            encrypted = API_KEYS_FILE.read_bytes()
            decrypted = self._fernet.decrypt(encrypted)
            data = json.loads(decrypted.decode())
            if not isinstance(data, dict):
                logger.warning("api keys storage corrompu (format invalide), reset")
                return {}
            return data
        except (InvalidToken, json.JSONDecodeError, OSError) as e:
            logger.warning(f"impossible de lire api keys storage: {type(e).__name__}")
            return {}

    def _save_all(self, data: Dict[str, str]) -> None:
        """Sauvegarde le dict complet des clés API (chiffré, atomique).

        Args:
            data: Dict avec clés `groq_api_key`, `openai_api_key`.
        """
        encrypted = self._fernet.encrypt(json.dumps(data).encode())
        fd = os.open(
            str(API_KEYS_FILE),
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600,
        )
        with os.fdopen(fd, "wb") as f:
            f.write(encrypted)

    def get_groq_key(self) -> Optional[str]:
        """Retourne la clé Groq stockée (déchiffrée), ou None si absente/vide.

        Returns:
            Clé Groq en clair, ou None.
        """
        data = self._load_all()
        key = data.get(_FIELD_GROQ, "").strip()
        return key or None

    def get_openai_key(self) -> Optional[str]:
        """Retourne la clé OpenAI stockée (déchiffrée), ou None si absente/vide.

        Returns:
            Clé OpenAI en clair, ou None.
        """
        data = self._load_all()
        key = data.get(_FIELD_OPENAI, "").strip()
        return key or None

    def set_groq_key(self, key: Optional[str]) -> None:
        """Sauvegarde une clé Groq (ou supprime si None/vide).

        Args:
            key: Clé Groq en clair, ou None/'' pour supprimer.
        """
        data = self._load_all()
        if key and key.strip():
            data[_FIELD_GROQ] = key.strip()
            logger.info("clé Groq mise à jour (BYOK)")
        else:
            data.pop(_FIELD_GROQ, None)
            logger.info("clé Groq retirée (BYOK)")
        self._save_all(data)

    def set_openai_key(self, key: Optional[str]) -> None:
        """Sauvegarde une clé OpenAI (ou supprime si None/vide).

        Args:
            key: Clé OpenAI en clair, ou None/'' pour supprimer.
        """
        data = self._load_all()
        if key and key.strip():
            data[_FIELD_OPENAI] = key.strip()
            logger.info("clé OpenAI mise à jour (BYOK)")
        else:
            data.pop(_FIELD_OPENAI, None)
            logger.info("clé OpenAI retirée (BYOK)")
        self._save_all(data)

    def has_any_key(self) -> bool:
        """Indique si au moins une clé API est configurée.

        Returns:
            True si Groq OU OpenAI est configurée.
        """
        return self.get_groq_key() is not None or self.get_openai_key() is not None

    def clear_all(self) -> None:
        """Supprime toutes les clés API stockées (efface le fichier)."""
        if API_KEYS_FILE.exists():
            API_KEYS_FILE.unlink()
            logger.info("toutes les clés API ont été supprimées (BYOK)")
