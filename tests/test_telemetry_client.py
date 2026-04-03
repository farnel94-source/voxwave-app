"""Tests pour le TelemetryClient."""

import time
import threading
from unittest.mock import patch, MagicMock

import pytest

from src.telemetry.client import TelemetryClient, VOXWAVE_DIR


class TestUUID:
    """Tests pour la génération et persistance de l'UUID."""

    def test_generates_uuid(self, tmp_path: "Path") -> None:
        """Un nouvel UUID est généré quand aucun fichier n'existe."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient()
            assert len(client.anonymous_id) == 36  # format UUID v4
            assert "-" in client.anonymous_id

    def test_persists_uuid_to_file(self, tmp_path: "Path") -> None:
        """L'UUID est sauvegardé dans le fichier device_id."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient()
            device_id_path = tmp_path / "device_id"
            assert device_id_path.exists()
            assert device_id_path.read_text().strip() == client.anonymous_id

    def test_reuses_existing_uuid(self, tmp_path: "Path") -> None:
        """Un UUID existant est réutilisé (pas de nouvelle génération)."""
        device_id_path = tmp_path / "device_id"
        device_id_path.write_text("existing-uuid-1234")
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient()
            assert client.anonymous_id == "existing-uuid-1234"

    def test_creates_directory_if_missing(self, tmp_path: "Path") -> None:
        """Le dossier .voxwave est créé s'il n'existe pas."""
        nested = tmp_path / "subdir" / ".voxwave"
        with patch("src.telemetry.client.VOXWAVE_DIR", nested):
            client = TelemetryClient()
            assert nested.exists()
            assert (nested / "device_id").exists()


class TestActivate:
    """Tests pour l'événement activate."""

    @patch("src.telemetry.client.requests.post")
    def test_sends_correct_payload(self, mock_post: MagicMock, tmp_path: "Path") -> None:
        """start() envoie un POST activate avec le bon payload."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient(language="fr", provider="cloud")
            client.start()
            time.sleep(0.5)
            client.stop()

        # Chercher l'appel activate parmi tous les appels
        activate_calls = [
            c for c in mock_post.call_args_list
            if "activate" in c[0][0]
        ]
        assert len(activate_calls) == 1
        payload = activate_calls[0][1]["json"]
        assert payload["anonymous_id"] == client.anonymous_id
        assert payload["language"] == "fr"
        assert payload["app_version"] is not None
        assert payload["os"] in ("windows", "linux")

    @patch("src.telemetry.client.requests.post")
    def test_disabled_sends_nothing(self, mock_post: MagicMock, tmp_path: "Path") -> None:
        """Quand disabled, start() n'envoie rien."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient(enabled=False)
            client.start()
            time.sleep(0.5)
            client.stop()

        # Aucun appel activate (le stop heartbeat est aussi bloqué)
        activate_calls = [
            c for c in mock_post.call_args_list
            if "activate" in str(c)
        ]
        assert len(activate_calls) == 0


class TestRecordDictation:
    """Tests pour le compteur de dictées."""

    @patch("src.telemetry.client.requests.post")
    def test_increments_counter(self, mock_post: MagicMock, tmp_path: "Path") -> None:
        """record_dictation() incrémente le compteur."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient()
            client.record_dictation()
            client.record_dictation()
            client.record_dictation()
            with client._lock:
                assert client._dictation_count == 3

    @patch("src.telemetry.client.requests.post")
    def test_thread_safe_increment(self, mock_post: MagicMock, tmp_path: "Path") -> None:
        """100 threads incrémentant en parallèle donnent exactement 100."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient()
            threads = []
            for _ in range(100):
                t = threading.Thread(target=client.record_dictation)
                threads.append(t)
                t.start()
            for t in threads:
                t.join()
            with client._lock:
                assert client._dictation_count == 100


class TestHeartbeat:
    """Tests pour le heartbeat."""

    @patch("src.telemetry.client.requests.post")
    def test_sends_dictation_count_and_resets(self, mock_post: MagicMock, tmp_path: "Path") -> None:
        """Le heartbeat envoie le compteur et le remet à zéro."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient(provider="local")
            client._start_time = time.monotonic()
            client.record_dictation()
            client.record_dictation()

            client._send_heartbeat()
            time.sleep(0.5)

        heartbeat_calls = [
            c for c in mock_post.call_args_list
            if "heartbeat" in c[0][0]
        ]
        assert len(heartbeat_calls) == 1
        payload = heartbeat_calls[0][1]["json"]
        assert payload["dictation_count"] == 2
        assert payload["provider"] == "local"
        assert payload["app_version"] is not None
        # Le compteur doit être remis à zéro
        with client._lock:
            assert client._dictation_count == 0

    @patch("src.telemetry.client.requests.post")
    def test_session_duration_correct(self, mock_post: MagicMock, tmp_path: "Path") -> None:
        """session_duration_s reflète le temps écoulé depuis start()."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient()
            client._start_time = time.monotonic() - 120  # 2 minutes ago

            client._send_heartbeat()
            time.sleep(0.5)

        heartbeat_calls = [
            c for c in mock_post.call_args_list
            if "heartbeat" in c[0][0]
        ]
        payload = heartbeat_calls[0][1]["json"]
        # Devrait être environ 120 secondes (avec une marge)
        assert 118 <= payload["session_duration_s"] <= 125


class TestError:
    """Tests pour les événements d'erreur."""

    @patch("src.telemetry.client.requests.post")
    def test_sends_correct_payload(self, mock_post: MagicMock, tmp_path: "Path") -> None:
        """record_error() envoie le bon payload."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient()
            client.record_error("TranscriptionError", "Groq timeout")
            time.sleep(0.5)

        error_calls = [
            c for c in mock_post.call_args_list
            if "error" in c[0][0]
        ]
        assert len(error_calls) == 1
        payload = error_calls[0][1]["json"]
        assert payload["anonymous_id"] == client.anonymous_id
        assert payload["error_type"] == "TranscriptionError"
        assert payload["error_message"] == "Groq timeout"
        assert payload["os"] in ("windows", "linux")

    @patch("src.telemetry.client.requests.post")
    def test_truncates_long_messages(self, mock_post: MagicMock, tmp_path: "Path") -> None:
        """Les messages d'erreur sont tronqués à 200 caractères."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient()
            long_message = "x" * 500
            client.record_error("CrashError", long_message)
            time.sleep(0.5)

        error_calls = [
            c for c in mock_post.call_args_list
            if "error" in c[0][0]
        ]
        payload = error_calls[0][1]["json"]
        assert len(payload["error_message"]) == 200


class TestStop:
    """Tests pour l'arrêt propre."""

    @patch("src.telemetry.client.requests.post")
    def test_sends_final_heartbeat(self, mock_post: MagicMock, tmp_path: "Path") -> None:
        """stop() envoie un dernier heartbeat."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient()
            client.start()
            time.sleep(0.5)
            client.record_dictation()
            client.stop()
            time.sleep(0.5)

        heartbeat_calls = [
            c for c in mock_post.call_args_list
            if "heartbeat" in c[0][0]
        ]
        assert len(heartbeat_calls) >= 1

    @patch("src.telemetry.client.requests.post")
    def test_cancels_timer(self, mock_post: MagicMock, tmp_path: "Path") -> None:
        """stop() annule le timer de heartbeat."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient()
            client.start()
            time.sleep(0.5)
            assert client._heartbeat_timer is not None
            client.stop()
            assert client._heartbeat_timer is None


class TestSetEnabled:
    """Tests pour le toggle enabled/disabled."""

    @patch("src.telemetry.client.requests.post")
    def test_disable_stops_heartbeat(self, mock_post: MagicMock, tmp_path: "Path") -> None:
        """Désactiver la télémétrie annule le timer heartbeat."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient()
            client.start()
            time.sleep(0.5)
            assert client._heartbeat_timer is not None
            client.set_enabled(False)
            assert client._heartbeat_timer is None
            # Cleanup
            client.stop()

    @patch("src.telemetry.client.requests.post")
    def test_disable_blocks_error_events(self, mock_post: MagicMock, tmp_path: "Path") -> None:
        """Quand désactivé, record_error() n'envoie rien."""
        with patch("src.telemetry.client.VOXWAVE_DIR", tmp_path):
            client = TelemetryClient()
            client.set_enabled(False)
            client.record_error("TestError", "should not send")
            time.sleep(0.5)

        error_calls = [
            c for c in mock_post.call_args_list
            if "error" in str(c)
        ]
        assert len(error_calls) == 0
