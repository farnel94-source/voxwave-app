"""VoxTool — Point d'entree principal.

Usage:
    python -m voxtool
    python -m voxtool --model small
    python -m voxtool --test
"""

import logging
import os
import sys
import threading
import time
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


class VoxTool:
    """Application principale VoxTool."""

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
        self._processing_thread: Optional[threading.Thread] = None
        self._processing_lock = threading.Lock()

    def initialize(self) -> None:
        """Initialise tous les composants."""
        from src.audio.capture import AudioCapture
        from src.audio.feedback import AudioFeedback
        from src.audio.processor import AudioProcessor
        from src.cleaning.llm_cleaner import CleaningPipeline
        from src.injection.keyboard import TextInjector
        from src.hotkey.listener import HotkeyListener

        logger.info("Initialisation VoxTool...")

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
        self.processor = AudioProcessor(sample_rate=self.config["audio"]["sample_rate"])

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
        )

        # System tray (PySide6 QSystemTrayIcon)
        from src.gui.tray_icon import TrayIcon
        self.tray = TrayIcon(
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_quit=self._shutdown,
            on_activate_license=self._activate_license_dialog,
        )
        self.tray.setup()

        # Prechargement du modele (local uniquement)
        if hasattr(self.engine, 'preload'):
            try:
                logger.info("Prechargement du modele Whisper...")
                self.engine.preload()
            except Exception as e:
                logger.error(f"Echec prechargement modele: {e}")
                logger.warning("Le modele sera charge au premier usage")
        logger.info("VoxTool pret !")

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
        self.feedback.play_stop()
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
                    self.tray.show_notification("VoxTool — Licence", msg)
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

            # Transcrire
            raw_text = self.engine.transcribe(audio)
            logger.info(f"Brut: {raw_text}")

            # Adapter les filler words a la langue detectee
            detected_lang = getattr(self.engine, "last_detected_language", None)
            if detected_lang:
                self.pipeline.regex_cleaner.set_language(detected_lang)

            if not raw_text.strip():
                logger.warning("Transcription vide")
                return

            # Filtrer les hallucinations connues de Whisper
            if is_hallucination(raw_text):
                logger.warning(f"Hallucination detectee, ignore: {raw_text}")
                return

            # Nettoyer
            clean_text = self.pipeline.clean(raw_text)
            logger.info(f"Propre: {clean_text}")

            if not clean_text.strip():
                logger.warning("Texte nettoye vide, ignore")
                return

            # Injecter
            self.injector.inject(clean_text)
            self.feedback.play_complete()
            logger.info("Texte injecte !")
        except Exception as e:
            had_error = True
            self.feedback.play_error()
            if self.tray:
                self.tray.set_state("error")
                self.tray.show_notification("VoxTool — Erreur", str(e))
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

    def _activate_license_dialog(self) -> None:
        """Ouvre un dialog pour saisir la cle de licence."""
        try:
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(
                None, "VoxTool — Activer licence",
                "Entrez votre cle de licence :"
            )
            if ok and text.strip():
                try:
                    self.license_validator.activate_license(text.strip())
                    if self.tray:
                        self.tray.show_notification("VoxTool", "Licence activee avec succes !")
                except Exception as e:
                    logger.error(f"Activation echouee: {e}")
                    if self.tray:
                        self.tray.show_notification("VoxTool — Erreur", f"Activation echouee : {e}")
        except Exception as e:
            logger.error(f"Dialog licence echoue: {e}")

    def _shutdown(self) -> None:
        """Arrete proprement tous les composants."""
        logger.info("Arret VoxTool...")
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
        # Quitter la boucle Qt
        if self._qt_app:
            self._qt_app.quit()

    def run(self) -> None:
        """Lance l'application avec boucle Qt."""
        from PySide6.QtWidgets import QApplication

        self._qt_app = QApplication.instance() or QApplication(sys.argv)
        self.initialize()
        self.listener.start()

        logger.info(f"VoxTool actif ! Hotkey: {self.config['hotkey']} — Fermez le tray pour quitter.")
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
    """VoxTool — Dictee vocale intelligente."""
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

    app = VoxTool(config)
    app.run()


if __name__ == "__main__":
    main()
