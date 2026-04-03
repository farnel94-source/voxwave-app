"""Client de télémétrie anonyme pour VoxWave.

Envoie des événements anonymes (activate, heartbeat, error) au backend.
Toutes les requêtes HTTP sont non-bloquantes (daemon threads).
La télémétrie n'est jamais critique : les erreurs sont loguées en DEBUG.
"""

import logging
import platform
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

import requests

from src import __version__

logger = logging.getLogger(__name__)

# Dossier de persistance (~/.voxwave/)
VOXWAVE_DIR = Path.home() / ".voxwave"

_BASE_URL = "https://voxwave-backend.onrender.com/api/telemetry"


def _get_os() -> str:
    """Retourne 'windows' ou 'linux' (les seules valeurs acceptées par le backend)."""
    if sys.platform == "win32":
        return "windows"
    return "linux"


class TelemetryClient:
    """Client de télémétrie anonyme.

    Génère un UUID persistant par machine, envoie des événements
    activate/heartbeat/error au backend VoxWave.
    """

    def __init__(
        self,
        language: str = "en",
        provider: str = "hybrid",
        enabled: bool = True,
    ) -> None:
        self._language = language
        self._provider = provider
        self._enabled = enabled

        self._anonymous_id = self._load_or_create_uuid()
        self._dictation_count = 0
        self._lock = threading.Lock()
        self._start_time: Optional[float] = None
        self._heartbeat_timer: Optional[threading.Timer] = None
        self._shutdown_event = threading.Event()

    # --- UUID persistence ---

    def _load_or_create_uuid(self) -> str:
        """Charge le device_id depuis le disque ou en génère un nouveau."""
        device_id_path = VOXWAVE_DIR / "device_id"
        try:
            if device_id_path.exists():
                stored = device_id_path.read_text().strip()
                if stored:
                    return stored
        except OSError:
            logger.debug("Impossible de lire le device_id existant")

        new_id = str(uuid.uuid4())
        try:
            VOXWAVE_DIR.mkdir(parents=True, exist_ok=True)
            device_id_path.write_text(new_id)
        except OSError:
            logger.debug("Impossible de sauvegarder le device_id")
        return new_id

    # --- Public API ---

    def start(self) -> None:
        """Envoie l'événement activate et démarre le heartbeat périodique."""
        self._start_time = time.monotonic()
        self._send_activate()
        self._schedule_heartbeat()

    def stop(self) -> None:
        """Arrête le heartbeat et envoie un dernier heartbeat (timeout 2s)."""
        self._shutdown_event.set()
        self._cancel_heartbeat()
        # Dernier heartbeat synchrone avec timeout court
        if self._enabled:
            self._send_heartbeat(timeout=2)

    def record_dictation(self) -> None:
        """Incrémente le compteur de dictées (thread-safe)."""
        with self._lock:
            self._dictation_count += 1

    def record_error(self, error_type: str, error_message: str) -> None:
        """Envoie un événement d'erreur au backend."""
        if not self._enabled:
            return
        # Tronquer le message à 200 caractères
        truncated_message = error_message[:200]
        payload = {
            "anonymous_id": self._anonymous_id,
            "error_type": error_type,
            "error_message": truncated_message,
            "app_version": __version__,
            "os": _get_os(),
        }
        self._post_async(f"{_BASE_URL}/error", payload)

    def set_enabled(self, enabled: bool) -> None:
        """Active ou désactive la télémétrie à chaud."""
        self._enabled = enabled
        if not enabled:
            self._cancel_heartbeat()

    @property
    def anonymous_id(self) -> str:
        """Retourne l'identifiant anonyme de cette machine."""
        return self._anonymous_id

    # --- Internal ---

    def _send_activate(self) -> None:
        """Envoie l'événement activate."""
        if not self._enabled:
            return
        payload = {
            "anonymous_id": self._anonymous_id,
            "os": _get_os(),
            "app_version": __version__,
            "language": self._language,
        }
        self._post_async(f"{_BASE_URL}/activate", payload)

    def _send_heartbeat(self, timeout: int = 5) -> None:
        """Envoie un heartbeat avec le compteur de dictées."""
        if not self._enabled:
            return

        with self._lock:
            count = self._dictation_count
            self._dictation_count = 0

        session_duration_s = 0
        if self._start_time is not None:
            session_duration_s = int(time.monotonic() - self._start_time)

        payload = {
            "anonymous_id": self._anonymous_id,
            "dictation_count": count,
            "provider": self._provider,
            "session_duration_s": session_duration_s,
            "app_version": __version__,
        }
        self._post_async(f"{_BASE_URL}/heartbeat", payload, timeout=timeout)

    def _schedule_heartbeat(self) -> None:
        """Planifie le prochain heartbeat dans 15 minutes."""
        if self._shutdown_event.is_set():
            return
        self._heartbeat_timer = threading.Timer(900, self._heartbeat_tick)
        self._heartbeat_timer.daemon = True
        self._heartbeat_timer.start()

    def _heartbeat_tick(self) -> None:
        """Callback du timer : envoie un heartbeat et replanifie."""
        if self._shutdown_event.is_set():
            return
        self._send_heartbeat()
        self._schedule_heartbeat()

    def _cancel_heartbeat(self) -> None:
        """Annule le timer de heartbeat en cours."""
        if self._heartbeat_timer is not None:
            self._heartbeat_timer.cancel()
            self._heartbeat_timer = None

    def _post_async(self, url: str, payload: dict, timeout: int = 5) -> None:
        """Envoie une requête POST dans un daemon thread."""
        thread = threading.Thread(
            target=self._do_post,
            args=(url, payload, timeout),
            daemon=True,
        )
        thread.start()

    def _do_post(self, url: str, payload: dict, timeout: int) -> None:
        """Effectue la requête POST (appelé dans un thread)."""
        try:
            requests.post(url, json=payload, timeout=timeout)
        except Exception:
            logger.debug("Échec envoi télémétrie vers %s", url)
