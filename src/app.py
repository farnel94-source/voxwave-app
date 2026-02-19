"""The Wave — Point d'entree principal.

Usage:
    python -m voxtool
    python -m voxtool --model small
    python -m voxtool --test
"""

import logging
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

# Fix encodage Unicode sur Windows (emojis dans le terminal)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import click
import yaml
from dotenv import load_dotenv

from src.transcription.hallucinations import is_hallucination

load_dotenv()

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def load_config(config_path: str = "config.yaml") -> dict:
    """Charge et valide la configuration.

    Args:
        config_path: Chemin vers config.yaml.

    Returns:
        Configuration validee et completee avec les defauts.
    """
    from src.config.validator import ConfigValidator
    from src.config.defaults import DEFAULT_CONFIG
    from src.utils.platform import resource_path

    # En mode PyInstaller, config.yaml est dans le bundle
    resolved_path = resource_path(config_path)

    try:
        with open(resolved_path, "r") as f:
            user_config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"Config {config_path} introuvable, utilisation des defauts")
        user_config = {}
    except yaml.YAMLError as e:
        logger.error(f"Erreur parsing config: {e}, utilisation des defauts")
        user_config = {}

    return ConfigValidator.validate_and_merge(user_config)


class _TaskbarWindow:
    """Fenetre fantome pour donner a l'app une presence dans la barre des taches Windows.

    Affichee comme minimisee (invisible) mais visible dans la barre des taches avec
    le logo The Wave. Clic sur l'icone -> ouvre les Parametres.
    """

    def __init__(self, on_activate, app_icon) -> None:
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QWidget

        class _Anchor(QWidget):
            def changeEvent(self_, event) -> None:  # noqa: N805
                from PySide6.QtCore import Qt
                if event.type() == QEvent.Type.WindowStateChange:
                    if not (self_.windowState() & Qt.WindowState.WindowMinimized):
                        self_.showMinimized()
                        on_activate()
                super(_Anchor, self_).changeEvent(event)

        self._win = _Anchor()
        self._win.setWindowTitle("The Wave")
        self._win.setWindowIcon(app_icon)
        self._win.showMinimized()


class TheWave:
    """Application principale The Wave."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.capture = None
        self.engine = None
        self.pipeline = None
        self.injector = None
        self.listener = None
        self.feedback = None
        self.tray = None
        self.waveform = None
        self.license_validator = None
        self._qt_app = None
        self._shutting_down = False
        self._processing_thread: Optional[threading.Thread] = None
        self._processing_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)

    def initialize(self) -> None:
        """Initialise tous les composants."""
        from src.audio.capture import AudioCapture
        from src.audio.feedback import AudioFeedback
        from src.audio.processor import AudioProcessor
        from src.cleaning.llm_cleaner import CleaningPipeline
        from src.injection.keyboard import TextInjector
        from src.hotkey.listener import HotkeyListener

        logger.info("Initialisation The Wave...")

        # Audio feedback
        feedback_config = self.config.get("audio", {}).get("feedback", {})
        self.feedback = AudioFeedback(
            enabled=feedback_config.get("enabled", True),
            volume=feedback_config.get("volume", 0.5),
        )

        # Valider le device_id si specifie
        from src.audio.device_manager import AudioDeviceManager
        device_id = self.config["audio"].get("device_id")
        device_id = AudioDeviceManager.validate_device(device_id)

        self.capture = AudioCapture(
            sample_rate=self.config["audio"]["sample_rate"],
            channels=self.config["audio"]["channels"],
            chunk_size=self.config["audio"]["chunk_size"],
            silence_threshold=self.config["audio"]["silence_threshold"],
            device_id=device_id,
        )
        vad_aggressiveness = self.config.get("audio", {}).get("vad_aggressiveness", 2)
        self.processor = AudioProcessor(
            sample_rate=self.config["audio"]["sample_rate"],
            vad_aggressiveness=vad_aggressiveness,
        )

        # Choix du moteur de transcription
        transcription_provider = self.config.get("transcription", {}).get("provider", "local")
        self.engine = self._create_transcription_engine(transcription_provider)

        # Choix du pipeline de nettoyage
        cleaning_config = self.config.get("cleaning", {})
        cleaning_provider = cleaning_config.get("provider", "local")
        cloud_model = cleaning_config.get("cloud_model", "gpt-4o-mini")
        filler_words = cleaning_config.get("filler_words")
        self.pipeline = CleaningPipeline(
            mode=cleaning_config["mode"],
            llm_model=cleaning_config["llm_model"],
            cloud_model=cloud_model,
            cleaning_provider=cleaning_provider,
            language=self.config["whisper"]["language"],
            filler_words=filler_words,
            on_fallback=self._on_fallback,
        )

        self.injector = TextInjector(mode=self.config["injection"])
        self.listener = HotkeyListener(
            hotkey=self.config["hotkey"],
            on_start=self._on_start,
            on_stop=self._on_stop,
            debounce_delay=self.config.get("hotkey_debounce", 0.5),
        )

        # Licensing
        from src.licensing.validator import LicenseValidator
        licensing_config = self.config.get("licensing", {})
        self.license_validator = LicenseValidator(
            free_daily_limit=licensing_config.get("free_daily_limit", 50),
            free_limit=licensing_config.get("free_limit", 1000),
            cache_duration=licensing_config.get("cache_duration", 86400),
        )

        # Waveform widget (PySide6 — cree apres QApplication)
        from src.gui.waveform_widget import WaveformWidget
        self.waveform = WaveformWidget(
            capture=self.capture,
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_settings=self._on_settings,
            on_quit=self._shutdown,
        )

        # System tray (PySide6 QSystemTrayIcon)
        from src.gui.tray_icon import TrayIcon
        self.tray = TrayIcon(
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_quit=self._shutdown,
            on_activate_license=self._activate_license_dialog,
            on_settings=self._on_settings,
            on_help=self._on_help,
            on_tray_clicked=self._on_settings,
        )
        self.tray.setup()

        # Pre-warm en background : charger Whisper + verifier Ollama
        self._prewarm_engines()
        logger.info("The Wave pret !")

    def _prewarm_engines(self) -> None:
        """Pre-charge les moteurs en background pour reduire la latence du premier appel."""
        def _prewarm_whisper() -> None:
            if hasattr(self.engine, 'preload'):
                try:
                    logger.info("Pre-warm: chargement modele Whisper...")
                    self.engine.preload()
                    logger.info("Pre-warm: modele Whisper charge")
                except Exception as e:
                    logger.warning(f"Pre-warm Whisper echec: {e}")

        def _prewarm_ollama() -> None:
            if self.pipeline and self.pipeline._local_cleaner:
                try:
                    available = self.pipeline._local_cleaner.is_available()
                    logger.info(f"Pre-warm: Ollama {'disponible' if available else 'indisponible'}")
                except Exception as e:
                    logger.warning(f"Pre-warm Ollama echec: {e}")

        def _check_cloud_connectivity() -> None:
            """Ping les APIs cloud et pre-ouvre les circuit breakers si injoignables."""
            import urllib.error
            import urllib.request
            # Check Groq
            if hasattr(self.engine, '_circuit'):
                try:
                    urllib.request.urlopen("https://api.groq.com", timeout=3)
                    logger.info("Pre-warm: Groq API joignable")
                except urllib.error.HTTPError:
                    # HTTP error = serveur joignable, juste pas de endpoint valide
                    logger.info("Pre-warm: Groq API joignable")
                except (urllib.error.URLError, OSError, TimeoutError):
                    logger.warning("Pre-warm: Groq API injoignable, circuit breaker pre-ouvert")
                    self.engine._circuit.force_open()
            # Check OpenAI
            if self.pipeline and self.pipeline._cloud_cleaner is not None:
                try:
                    urllib.request.urlopen("https://api.openai.com", timeout=3)
                    logger.info("Pre-warm: OpenAI API joignable")
                except urllib.error.HTTPError:
                    logger.info("Pre-warm: OpenAI API joignable")
                except (urllib.error.URLError, OSError, TimeoutError):
                    logger.warning("Pre-warm: OpenAI API injoignable, circuit breaker pre-ouvert")
                    self.pipeline._cloud_circuit.force_open()

        self._executor.submit(_prewarm_whisper)
        self._executor.submit(_prewarm_ollama)
        self._executor.submit(_check_cloud_connectivity)

    def _create_transcription_engine(self, provider: str) -> object:
        """Cree le moteur de transcription selon le provider configure.

        Args:
            provider: hybrid, cloud, ou local.

        Returns:
            Instance du moteur de transcription.
        """
        language = self.config["whisper"]["language"]
        sample_rate = self.config["audio"]["sample_rate"]

        if provider == "hybrid":
            from src.transcription.hybrid_engine import HybridTranscriptionEngine
            groq_model = self.config.get("groq", {}).get("model", "whisper-large-v3")
            return HybridTranscriptionEngine(
                groq_model=groq_model,
                local_model=self.config["whisper"]["model"],
                language=language,
                sample_rate=sample_rate,
                on_fallback=self._on_fallback,
            )
        elif provider == "cloud":
            from src.transcription.groq_engine import GroqWhisperEngine
            groq_model = self.config.get("groq", {}).get("model", "whisper-large-v3")
            return GroqWhisperEngine(
                model=groq_model, language=language, sample_rate=sample_rate,
            )
        else:
            from src.transcription.whisper_engine import WhisperEngine
            return WhisperEngine(
                model=self.config["whisper"]["model"],
                language=language,
                sample_rate=sample_rate,
            )

    def _toggle_waveform(self) -> None:
        """Affiche ou cache le widget orb quand on clique sur l'icone tray."""
        if self.waveform:
            if self.waveform.isVisible():
                self.waveform.hide()
            else:
                self.waveform.show()
                self.waveform.raise_()

    def _on_start(self) -> None:
        """Callback: debut enregistrement."""
        logger.info("Enregistrement...")
        self.feedback.play_start()
        if self.tray:
            self.tray.set_state("recording")
        if self.waveform:
            self.waveform.show_recording()
        self.capture.start()

    def _on_stop(self) -> None:
        """Callback: fin enregistrement -> lance le pipeline dans un thread."""
        if self.tray:
            self.tray.set_state("processing")
        if self.waveform:
            self.waveform.show_processing()
        self.capture.stop()
        audio = self.capture.get_buffer()

        if len(audio) == 0:
            logger.warning("Aucun audio capture")
            if self.waveform:
                self.waveform.show_idle()
            return

        # Jouer le son stop en background (overlap avec debut du pipeline)
        self._executor.submit(self.feedback.play_stop)

        # Lancer le pipeline dans un thread pour ne pas bloquer le listener
        self._processing_thread = threading.Thread(
            target=self._process_audio, args=(audio,), daemon=True,
        )
        self._processing_thread.start()

    def _process_audio(self, audio) -> None:
        """Pipeline complet : transcription -> nettoyage -> injection (thread separe)."""
        if not self._processing_lock.acquire(blocking=False):
            logger.warning("Pipeline deja en cours, appui ignore")
            return
        self.listener.set_processing(True)
        had_error = False
        try:
            # Verifier la licence / free tier
            if self.license_validator and not self.license_validator.increment_usage():
                msg = "Free tier epuise. Activez une licence pour continuer."
                logger.warning(msg)
                if self.tray:
                    self.tray.show_notification("The Wave — Licence", msg)
                return

            audio_config = self.config["audio"]
            duration = len(audio) / audio_config["sample_rate"]
            min_duration = audio_config.get("min_audio_duration", 0.5)
            max_duration = audio_config.get("max_audio_duration", 120.0)
            logger.info(f"Audio capture: {duration:.2f}s")

            if duration < min_duration:
                logger.warning(f"Audio trop court ({duration:.2f}s < {min_duration}s), ignore")
                return

            if duration > max_duration:
                logger.warning(f"Audio trop long ({duration:.2f}s), tronque a {max_duration}s")
                max_samples = int(max_duration * audio_config["sample_rate"])
                audio = audio[:max_samples]

            # Preparer (apres troncature)
            audio = self.processor.prepare_for_whisper(audio)

            # Verifier la taille apres preparation (limite Groq API : 25MB WAV)
            audio_size_bytes = len(audio) * 2
            if audio_size_bytes > 24_000_000:
                max_safe_samples = 24_000_000 // 2
                logger.warning(f"Audio trop volumineux ({audio_size_bytes/1e6:.1f}MB), tronque pour API")
                audio = audio[:max_safe_samples]

            # Chunking si audio long
            chunking_threshold = self.config.get("audio", {}).get("chunking_threshold", 30.0)
            audio_duration = len(audio) / self.config["audio"]["sample_rate"]

            # Indicateur d'etape
            if self.waveform:
                self.waveform.update_step("Transcription...")

            if audio_duration > chunking_threshold:
                clean_text = self._process_chunked(audio)
            else:
                clean_text = self._transcribe_and_clean(audio)

            if not clean_text or not clean_text.strip():
                logger.warning("Texte final vide, ignore")
                return

            # Apercu transcription
            show_preview = self.config.get("gui", {}).get("show_transcription_preview", True)
            if self.waveform and show_preview:
                self.waveform.show_preview(clean_text)

            # Injecter
            if self.waveform:
                self.waveform.update_step("Injection...")
            self.injector.inject(clean_text)
            self.feedback.play_complete()
            logger.info("Texte injecte !")
        except Exception as e:
            had_error = True
            self.feedback.play_error()
            if self.tray:
                self.tray.set_state("error")
                self.tray.show_notification("The Wave — Erreur", str(e))
            if self.waveform:
                self.waveform.show_error()  # revient a idle apres ERROR_DISPLAY_MS
            from src.utils.exceptions import TranscriptionError, CleaningError
            if isinstance(e, TranscriptionError):
                logger.error(f"Erreur transcription: {e}")
            elif isinstance(e, CleaningError):
                logger.error(f"Erreur nettoyage: {e}")
            else:
                logger.error(f"Erreur pipeline inattendue: {e}", exc_info=True)
        finally:
            self._processing_lock.release()
            self.listener.set_processing(False)
            if not had_error:
                if self.waveform:
                    self.waveform.show_idle()
                if self.tray:
                    self.tray.set_state("idle")

    def _transcribe_and_clean(self, audio) -> Optional[str]:
        """Transcrit et nettoie un segment audio.

        Args:
            audio: Buffer audio float32.

        Returns:
            Texte nettoye ou None.
        """
        # Transcrire
        raw_text = self.engine.transcribe(audio)
        logger.info(f"Brut: {raw_text}")

        # Adapter les filler words a la langue detectee
        detected_lang = getattr(self.engine, "last_detected_language", None)
        if detected_lang:
            self.pipeline.regex_cleaner.set_language(detected_lang)

        if not raw_text.strip():
            logger.warning("Transcription vide")
            return None

        # Filtrer les hallucinations connues de Whisper
        if is_hallucination(raw_text):
            logger.warning(f"Hallucination detectee, ignore: {raw_text}")
            return None

        # Nettoyer
        if self.waveform:
            self.waveform.update_step("Nettoyage...")
        clean_text = self.pipeline.clean(raw_text)
        logger.info(f"Propre: {clean_text}")

        if not clean_text.strip():
            logger.warning("Texte nettoye vide, ignore")
            return None

        return clean_text

    def _process_chunked(self, audio) -> Optional[str]:
        """Traite un audio long par chunks avec progress.

        Args:
            audio: Buffer audio float32.

        Returns:
            Texte complet nettoye ou None.
        """
        chunks = self.processor.split_at_silence(audio)
        total = len(chunks)
        logger.info(f"Traitement chunke: {total} chunks")

        results = []
        for i, chunk in enumerate(chunks):
            if self.waveform:
                self.waveform.update_step(f"Transcription {i+1}/{total}...")
            result = self._transcribe_and_clean(chunk)
            if result:
                results.append(result)

        if not results:
            return None

        return " ".join(results)

    def _activate_license_dialog(self) -> None:
        """Ouvre un dialog pour saisir la cle de licence."""
        try:
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(
                None, "The Wave — Activer licence",
                "Entrez votre cle de licence :"
            )
            if ok and text.strip():
                try:
                    self.license_validator.activate_license(text.strip())
                    if self.tray:
                        self.tray.show_notification("The Wave", "Licence activee avec succes !")
                except Exception as e:
                    logger.error(f"Activation echouee: {e}")
                    if self.tray:
                        self.tray.show_notification("The Wave — Erreur", f"Activation echouee : {e}")
        except Exception as e:
            logger.error(f"Dialog licence echoue: {e}")

    def _on_settings(self) -> None:
        """Ouvre le dialogue des parametres et applique les changements."""
        from src.gui.settings_dialog import SettingsDialog

        cleaning_config = self.config.get("cleaning", {})
        dialog = SettingsDialog(
            current_hotkey=self.config["hotkey"],
            current_cleaning_mode=cleaning_config.get("mode", "verbatim"),
            current_language=self.config.get("whisper", {}).get("language", "en"),
            current_system_language=self.config.get("language", "en"),
            current_device_id=self.config.get("audio", {}).get("device_id"),
            current_transcription_provider=self.config.get("transcription", {}).get("provider", "hybrid"),
            current_cleaning_provider=cleaning_config.get("provider", "hybrid"),
            current_activation_method=self.config.get("activation_method", "both"),
            on_quit=self._shutdown,
            on_activate_license=self._activate_license_dialog,
        )
        dialog.exec()  # on lance toujours (fermeture avec X ou Save sauvegarde quand meme)
        changes = []

        # Hotkey
        new_hotkey = dialog.hotkey
        if new_hotkey != self.config["hotkey"]:
            self.config["hotkey"] = new_hotkey
            if self.listener:
                self.listener.update_hotkey(new_hotkey)
            self._save_config("hotkey", new_hotkey)
            changes.append(f"Raccourci : {new_hotkey}")

        # Cleaning mode
        new_mode = dialog.cleaning_mode
        if new_mode != cleaning_config.get("mode"):
            self.config.setdefault("cleaning", {})["mode"] = new_mode
            if self.pipeline:
                self.pipeline.mode = new_mode
            self._save_config_nested("cleaning", "mode", new_mode)
            mode_names = {"raw": "Brut", "verbatim": "Naturel", "quality": "Professionnel"}
            changes.append(f"Mode : {mode_names.get(new_mode, new_mode)}")

        # System language (interface)
        new_sys_lang = dialog.system_language
        if new_sys_lang != self.config.get("language"):
            self.config["language"] = new_sys_lang
            self._save_config("language", new_sys_lang)
            changes.append(f"Interface : {new_sys_lang}")

        # Dictation language
        new_lang = dialog.language
        if new_lang != self.config.get("whisper", {}).get("language"):
            self.config.setdefault("whisper", {})["language"] = new_lang
            self._save_config_nested("whisper", "language", new_lang)
            # Mettre a jour le moteur a runtime (sans redemarrer)
            if hasattr(self.engine, "language"):
                self.engine.language = new_lang
            if self.pipeline and hasattr(self.pipeline, "language"):
                self.pipeline.language = new_lang
            changes.append(f"Dictee : {new_lang}")

        # Device ID
        new_device = dialog.device_id
        if new_device != self.config.get("audio", {}).get("device_id"):
            self.config.setdefault("audio", {})["device_id"] = new_device
            self._save_config_nested("audio", "device_id", new_device)
            changes.append("Micro change")

        # Transcription provider
        new_trans = dialog.transcription_provider
        if new_trans != self.config.get("transcription", {}).get("provider"):
            self.config.setdefault("transcription", {})["provider"] = new_trans
            self._save_config_nested("transcription", "provider", new_trans)
            changes.append(f"Transcription : {new_trans}")

        # Cleaning provider
        new_clean = dialog.cleaning_provider
        if new_clean != cleaning_config.get("provider"):
            self.config.setdefault("cleaning", {})["provider"] = new_clean
            self._save_config_nested("cleaning", "provider", new_clean)
            changes.append(f"Nettoyage : {new_clean}")

        # Activation method (hotkey / icon / both)
        new_activation = dialog.activation_method
        if new_activation != self.config.get("activation_method", "both"):
            self.config["activation_method"] = new_activation
            self._save_config("activation_method", new_activation)
            if new_activation == "icon":
                if self.listener:
                    self.listener.stop()
            else:
                if self.listener:
                    self.listener.start()
            changes.append(f"Activation : {new_activation}")

        if changes and self.tray:
            self.tray.show_notification("The Wave", "Parametres mis a jour")
        logger.info(f"Settings: {', '.join(changes) if changes else 'aucun changement'}")

    def _on_help(self) -> None:
        """Ouvre les parametres sur l'onglet Aide."""
        from src.gui.settings_dialog import SettingsDialog

        cleaning_config = self.config.get("cleaning", {})
        dialog = SettingsDialog(
            current_hotkey=self.config["hotkey"],
            current_cleaning_mode=cleaning_config.get("mode", "verbatim"),
            current_language=self.config.get("whisper", {}).get("language", "en"),
            current_system_language=self.config.get("language", "en"),
            current_device_id=self.config.get("audio", {}).get("device_id"),
            current_transcription_provider=self.config.get("transcription", {}).get("provider", "hybrid"),
            current_cleaning_provider=cleaning_config.get("provider", "hybrid"),
            current_activation_method=self.config.get("activation_method", "both"),
            on_quit=self._shutdown,
            on_activate_license=self._activate_license_dialog,
        )
        dialog.navigate_to_help()
        dialog.exec()

    def _save_config(self, key: str, value: object) -> None:
        """Sauvegarde un champ dans config.yaml en preservant le reste.

        Args:
            key: Cle de premier niveau a mettre a jour.
            value: Nouvelle valeur.
        """
        from src.utils.platform import resource_path

        config_path = resource_path("config.yaml")
        try:
            with open(config_path, "r") as f:
                lines = f.readlines()

            # Chercher et remplacer la ligne correspondante
            new_lines = []
            found = False
            for line in lines:
                if line.startswith(f"{key}:"):
                    new_lines.append(f"{key}: {value}\n")
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                new_lines.append(f"{key}: {value}\n")

            with open(config_path, "w") as f:
                f.writelines(new_lines)

            logger.info(f"Config sauvegardee: {key}={value}")
        except Exception as e:
            logger.error(f"Erreur sauvegarde config: {e}")

    def _save_config_nested(self, section: str, key: str, value: object) -> None:
        """Sauvegarde une cle nested dans config.yaml (ex: cleaning.mode).

        Charge le YAML complet, modifie la cle, et re-ecrit le fichier.

        Args:
            section: Section de premier niveau (ex: "cleaning").
            key: Cle dans la section (ex: "mode").
            value: Nouvelle valeur.
        """
        from src.utils.platform import resource_path

        config_path = resource_path("config.yaml")
        try:
            with open(config_path, "r") as f:
                data = yaml.safe_load(f) or {}

            if section not in data:
                data[section] = {}
            data[section][key] = value

            with open(config_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            logger.info(f"Config sauvegardee: {section}.{key}={value}")
        except Exception as e:
            logger.error(f"Erreur sauvegarde config nested: {e}")

    def _on_fallback(self, message: str) -> None:
        """Affiche une notification de fallback via le tray.

        Args:
            message: Message de fallback a afficher.
        """
        logger.info(f"Fallback: {message}")
        if self.tray:
            self.tray.show_notification("The Wave", message)

    def _shutdown(self) -> None:
        """Arrete proprement tous les composants (idempotent)."""
        if self._shutting_down:
            return
        self._shutting_down = True
        logger.info("Arret The Wave...")
        if self.listener:
            self.listener.stop()
        if self._processing_thread and self._processing_thread.is_alive():
            logger.info("Attente fin du pipeline en cours...")
            self._processing_thread.join(timeout=10)
            if self._processing_thread.is_alive():
                logger.warning("Pipeline toujours en cours apres 10s, arret force")
        if self.capture:
            self.capture.stop()
        if self.waveform:
            self.waveform.show_idle()
        # Shutdown executor
        self._executor.shutdown(wait=False)
        # Quitter la boucle Qt
        if self._qt_app:
            self._qt_app.quit()

    def run(self) -> None:
        """Lance l'application avec boucle Qt."""
        # The Wave cible Windows et Linux uniquement
        if sys.platform == "darwin":
            logger.error("The Wave n'est pas supporte sur macOS. Utilisez Windows ou Linux.")
            print("The Wave n'est pas supporte sur macOS.")
            print("Plateformes supportees : Windows, Linux.")
            sys.exit(1)

        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        self._qt_app = QApplication.instance() or QApplication(sys.argv)
        self._qt_app.setQuitOnLastWindowClosed(False)
        from src.gui.icons import create_qicon
        _app_icon = create_qicon("idle")
        self._qt_app.setWindowIcon(_app_icon)
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.thewave.app")
        self._taskbar = _TaskbarWindow(on_activate=self._on_settings, app_icon=_app_icon)
        self.initialize()

        # Welcome screen au premier lancement
        if self.config.get("first_launch", True):
            from src.gui.welcome_dialog import WelcomeDialog
            dialog = WelcomeDialog(
                current_hotkey=self.config["hotkey"],
                engine=self.engine,
                processor=self.processor,
                feedback=self.feedback,
                parent=None,
            )
            if dialog.exec():
                # Appliquer le hotkey choisi
                new_hotkey = dialog.hotkey
                if new_hotkey != self.config["hotkey"]:
                    self.config["hotkey"] = new_hotkey
                    if self.listener:
                        self.listener.update_hotkey(new_hotkey)
                    self._save_config("hotkey", new_hotkey)
                # Appliquer le mode de nettoyage choisi
                new_mode = dialog.cleaning_mode
                if new_mode != self.config.get("cleaning", {}).get("mode"):
                    self.config.setdefault("cleaning", {})["mode"] = new_mode
                    if self.pipeline:
                        self.pipeline.mode = new_mode
                    self._save_config_nested("cleaning", "mode", new_mode)
                # Appliquer la langue choisie (interface + dictee)
                new_lang = dialog.language
                if new_lang != self.config.get("language"):
                    self.config["language"] = new_lang
                    self._save_config("language", new_lang)
                if new_lang != self.config.get("whisper", {}).get("language"):
                    self.config.setdefault("whisper", {})["language"] = new_lang
                    self._save_config_nested("whisper", "language", new_lang)
                # Marquer le premier lancement comme termine
                self.config["first_launch"] = False
                self._save_config("first_launch", "false")

        self.listener.start()

        # Signal handlers pour shutdown propre (Ctrl+C, SIGTERM)
        def _signal_handler(signum: int, frame: object) -> None:
            sig_name = signal.Signals(signum).name
            logger.info(f"Signal {sig_name} recu, arret en cours...")
            self._shutdown()

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        # QTimer no-op pour que Python puisse traiter les signaux
        # pendant la boucle Qt (sinon exec() bloque les handlers)
        self._signal_timer = QTimer()
        self._signal_timer.timeout.connect(lambda: None)
        self._signal_timer.start(500)

        logger.info(f"The Wave actif ! Hotkey: {self.config['hotkey']} — Fermez le tray pour quitter.")
        self._qt_app.exec()


def test_microphone(config: dict) -> None:
    """Test rapide du microphone."""
    from src.audio.capture import AudioCapture
    import numpy as np

    print("Test du microphone (3 secondes)...")
    capture = AudioCapture(
        sample_rate=config["audio"]["sample_rate"],
        channels=config["audio"]["channels"],
    )
    capture.start()
    time.sleep(3)
    capture.stop()
    audio = capture.get_buffer()

    if len(audio) == 0:
        print("Aucun audio capture ! Verifiez votre micro.")
    else:
        volume = np.abs(audio).mean()
        duration = len(audio) / config["audio"]["sample_rate"]
        print(f"Audio capture: {duration:.1f}s, volume moyen: {volume:.4f}")
        if volume < 0.001:
            print("Volume tres faible. Verifiez votre micro.")
        else:
            print("Micro OK !")


@click.command()
@click.option("--model", default=None, help="Modele Whisper (tiny/base/small/medium/large-v3)")
@click.option("--test", is_flag=True, help="Test du microphone")
@click.option("--list-devices", is_flag=True, help="Liste les peripheriques audio")
@click.option("--config", "config_path", default="config.yaml", help="Chemin config")
@click.option("--log-level", default=None, help="Niveau de log")
def main(model, test, list_devices, config_path, log_level):
    """The Wave — Dictee vocale intelligente."""
    effective_log_level = log_level or os.getenv("VOXTOOL_LOG_LEVEL", "INFO")
    setup_logging(effective_log_level)
    config = load_config(config_path)

    if list_devices:
        from src.audio.device_manager import AudioDeviceManager
        AudioDeviceManager.print_devices()
        return

    if model:
        config["whisper"]["model"] = model

    if test:
        test_microphone(config)
        return

    app = TheWave(config)
    app.run()


if __name__ == "__main__":
    main()
