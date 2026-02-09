"""VoxTool — Point d'entrée principal.

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

# Fix encodage Unicode sur Windows (emojis dans le terminal)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import click
import yaml
from dotenv import load_dotenv

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
        Configuration validée et complétée avec les défauts.
    """
    from src.config.validator import ConfigValidator
    from src.config.defaults import DEFAULT_CONFIG

    try:
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"Config {config_path} introuvable, utilisation des défauts")
        user_config = {}
    except yaml.YAMLError as e:
        logger.error(f"Erreur parsing config: {e}, utilisation des défauts")
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
        self.license_validator = None

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

        # Valider le device_id si spécifié
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
        cleaning_provider = self.config.get("cleaning", {}).get("provider", "local")
        cloud_model = self.config.get("cleaning", {}).get("cloud_model", "gpt-4o-mini")
        self.pipeline = CleaningPipeline(
            mode=self.config["cleaning"]["mode"],
            llm_model=self.config["cleaning"]["llm_model"],
            cloud_model=cloud_model,
            cleaning_provider=cleaning_provider,
        )

        self.injector = TextInjector(mode=self.config["injection"])
        self.listener = HotkeyListener(
            hotkey=self.config["hotkey"],
            on_start=self._on_start,
            on_stop=self._on_stop,
        )

        # Licensing
        from src.licensing.validator import LicenseValidator
        licensing_config = self.config.get("licensing", {})
        self.license_validator = LicenseValidator(
            free_limit=licensing_config.get("free_limit", 1000),
            cache_duration=licensing_config.get("cache_duration", 86400),
        )

        # System tray
        from src.gui.tray_icon import TrayIcon
        self.tray = TrayIcon(
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_quit=self._shutdown,
            on_activate_license=self._activate_license_dialog,
        )

        # Précharge le modèle (local uniquement)
        if hasattr(self.engine, '_load_model'):
            logger.info("Préchargement du modèle Whisper...")
            self.engine._load_model()
        logger.info("VoxTool prêt !")

    def _create_transcription_engine(self, provider: str) -> object:
        """Crée le moteur de transcription selon le provider configuré.

        Args:
            provider: hybrid, cloud, ou local.

        Returns:
            Instance du moteur de transcription.
        """
        language = self.config["whisper"]["language"]

        if provider == "hybrid":
            from src.transcription.hybrid_engine import HybridTranscriptionEngine
            groq_model = self.config.get("groq", {}).get("model", "whisper-large-v3")
            return HybridTranscriptionEngine(
                groq_model=groq_model,
                local_model=self.config["whisper"]["model"],
                language=language,
            )
        elif provider == "cloud":
            from src.transcription.groq_engine import GroqWhisperEngine
            groq_model = self.config.get("groq", {}).get("model", "whisper-large-v3")
            return GroqWhisperEngine(model=groq_model, language=language)
        else:
            from src.transcription.whisper_engine import WhisperEngine
            return WhisperEngine(
                model=self.config["whisper"]["model"],
                language=language,
            )

    def _on_start(self) -> None:
        """Callback: début enregistrement."""
        logger.info("🔴 Enregistrement...")
        self.feedback.play_start()
        if self.tray:
            self.tray.set_state("recording")
        self.capture.start()

    def _on_stop(self) -> None:
        """Callback: fin enregistrement → lance le pipeline dans un thread."""
        self.feedback.play_stop()
        if self.tray:
            self.tray.set_state("processing")
        self.capture.stop()
        audio = self.capture.get_buffer()

        if len(audio) == 0:
            logger.warning("Aucun audio capturé")
            return

        # Lancer le pipeline dans un thread pour ne pas bloquer le listener
        thread = threading.Thread(target=self._process_audio, args=(audio,), daemon=True)
        thread.start()

    # Durées min/max pour éviter les hallucinations Whisper/Groq
    MIN_AUDIO_DURATION = 0.5  # secondes
    MAX_AUDIO_DURATION = 120.0  # secondes

    def _process_audio(self, audio) -> None:
        """Pipeline complet : transcription → nettoyage → injection (thread séparé)."""
        self.listener.set_processing(True)
        try:
            # Vérifier la licence / free tier
            if self.license_validator and not self.license_validator.increment_usage():
                msg = "Free tier épuisé. Activez une licence pour continuer."
                logger.warning(msg)
                if self.tray:
                    self.tray.show_notification("VoxTool — Licence", msg)
                return

            duration = len(audio) / self.config["audio"]["sample_rate"]
            logger.info(f"Audio capturé: {duration:.2f}s")

            if duration < self.MIN_AUDIO_DURATION:
                logger.warning(f"Audio trop court ({duration:.2f}s < {self.MIN_AUDIO_DURATION}s), ignoré")
                return

            if duration > self.MAX_AUDIO_DURATION:
                logger.warning(f"Audio trop long ({duration:.2f}s), tronqué")
                max_samples = int(self.MAX_AUDIO_DURATION * self.config["audio"]["sample_rate"])
                audio = audio[:max_samples]

            # Préparer
            audio = self.processor.prepare_for_whisper(audio)

            # Transcrire
            raw_text = self.engine.transcribe(audio)
            logger.info(f"Brut: {raw_text}")

            if not raw_text.strip():
                logger.warning("Transcription vide")
                return

            # Filtrer les hallucinations connues de Whisper
            if self._is_hallucination(raw_text):
                logger.warning(f"Hallucination détectée, ignoré: {raw_text}")
                return

            # Nettoyer
            clean_text = self.pipeline.clean(raw_text)
            logger.info(f"Propre: {clean_text}")

            if not clean_text.strip():
                logger.warning("Texte nettoyé vide, ignoré")
                return

            # Injecter
            self.injector.inject(clean_text)
            self.feedback.play_complete()
            logger.info("Texte injecté !")
        except Exception as e:
            self.feedback.play_error()
            if self.tray:
                self.tray.set_state("error")
                self.tray.show_notification("VoxTool — Erreur", str(e))
            from src.utils.exceptions import TranscriptionError, CleaningError
            if isinstance(e, TranscriptionError):
                logger.error(f"Erreur transcription: {e}")
            elif isinstance(e, CleaningError):
                logger.error(f"Erreur nettoyage: {e}")
            else:
                logger.error(f"Erreur pipeline inattendue: {e}", exc_info=True)
        finally:
            self.listener.set_processing(False)
            # Revenir à idle après un délai si erreur, sinon immédiatement
            if self.tray:
                self.tray.set_state("idle")

    @staticmethod
    def _is_hallucination(text: str) -> bool:
        """Détecte les hallucinations typiques de Whisper/Groq.

        Args:
            text: Texte transcrit.

        Returns:
            True si c'est probablement une hallucination.
        """
        text_lower = text.strip().lower()
        # Phrases génériques que Whisper hallucine sur du silence/bruit
        hallucinations = [
            "merci.", "merci !", "merci",
            "sous-titrage", "sous-titres",
            "merci d'avoir regardé", "merci d'avoir regardé !",
            "merci d'avoir regardé cette vidéo",
            "merci d'avoir regardé cette vidéo !",
            "merci de votre attention",
            "merci de votre attention.",
            "à bientôt", "à bientôt.",
            "au revoir", "au revoir.",
            "...", "…",
            "bye", "bye.",
            "thank you", "thanks",
            "thank you for watching",
            "thanks for watching",
            "et oui.", "et oui",
        ]
        # Match exact ou le texte commence par une hallucination connue
        if text_lower in hallucinations:
            return True
        # Texte trop court et générique = probable hallucination
        if len(text_lower) < 15 and text_lower.count(" ") <= 2:
            generic = ["oui", "non", "ok", "bon", "bien", "ah", "oh",
                        "hmm", "hm", "ha", "et oui", "et non", "voilà"]
            stripped = text_lower.rstrip(".!? ")
            if stripped in generic:
                return True
        return False

    def _activate_license_dialog(self) -> None:
        """Ouvre un dialog tkinter pour saisir la clé de licence."""
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.title("VoxTool — Activer licence")
            root.geometry("400x150")
            root.resizable(False, False)

            tk.Label(root, text="Entrez votre clé de licence :").pack(pady=(15, 5))
            entry = tk.Entry(root, width=50)
            entry.pack(pady=5)

            def activate():
                key = entry.get().strip()
                if not key:
                    messagebox.showwarning("Erreur", "Veuillez entrer une clé.")
                    return
                try:
                    self.license_validator.activate_license(key)
                    messagebox.showinfo("Succès", "Licence activée avec succès !")
                    if self.tray:
                        self.tray.show_notification("VoxTool", "Licence activée !")
                    root.destroy()
                except Exception as e:
                    messagebox.showerror("Erreur", f"Activation échouée : {e}")

            tk.Button(root, text="Activer", command=activate).pack(pady=10)
            root.mainloop()
        except Exception as e:
            logger.error(f"Dialog licence échoué: {e}")

    def _shutdown(self) -> None:
        """Arrête proprement tous les composants."""
        logger.info("Arrêt VoxTool...")
        if self.listener:
            self.listener.stop()
        if self.capture and self.capture.is_recording:
            self.capture.stop()

    def run(self) -> None:
        """Lance l'application avec system tray."""
        self.initialize()
        self.listener.start()
        logger.info(f"VoxTool actif ! Hotkey: {self.config['hotkey']}")

        # Lancer le tray en mode non-bloquant (thread séparé)
        # pour ne pas bloquer le hotkey listener pynput
        self.tray.run_detached()

        print(f"\n🎙️ VoxTool actif ! Appuyez sur {self.config['hotkey']} pour dicter.")
        print("   Ctrl+C pour quitter.\n")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self._shutdown()
            if self.tray:
                self.tray.stop()


def test_microphone(config: dict) -> None:
    """Test rapide du microphone."""
    from src.audio.capture import AudioCapture
    import numpy as np

    print("🎤 Test du microphone (3 secondes)...")
    capture = AudioCapture(
        sample_rate=config["audio"]["sample_rate"],
        channels=config["audio"]["channels"],
    )
    capture.start()
    time.sleep(3)
    capture.stop()
    audio = capture.get_buffer()

    if len(audio) == 0:
        print("❌ Aucun audio capturé ! Vérifiez votre micro.")
    else:
        volume = np.abs(audio).mean()
        duration = len(audio) / config["audio"]["sample_rate"]
        print(f"✅ Audio capturé: {duration:.1f}s, volume moyen: {volume:.4f}")
        if volume < 0.001:
            print("⚠️ Volume très faible. Vérifiez votre micro.")
        else:
            print("🎉 Micro OK !")


@click.command()
@click.option("--model", default=None, help="Modèle Whisper (tiny/base/small/medium/large-v3)")
@click.option("--test", is_flag=True, help="Test du microphone")
@click.option("--list-devices", is_flag=True, help="Liste les périphériques audio")
@click.option("--config", "config_path", default="config.yaml", help="Chemin config")
@click.option("--log-level", default="INFO", help="Niveau de log")
def main(model, test, list_devices, config_path, log_level):
    """VoxTool — Dictée vocale intelligente."""
    setup_logging(log_level)
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
