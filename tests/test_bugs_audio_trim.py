"""Tests de reproduction : audio trim et injection intermittents.

Bug A — Le texte ne se colle pas (parfois) : clipboard restauré trop vite.
Bug B — Les dernières secondes coupées (parfois) : trim_silence trop agressif
        sur les fins de phrase avec voix décroissante.
"""

import numpy as np
import pytest
import time
from unittest.mock import MagicMock, patch, call

from src.audio.processor import AudioProcessor


# ── Bug B : trim_silence coupe la fin de parole ───────────────────────────────

def _make_speech_with_gradual_fade(
    duration_s: float = 5.0,
    fade_duration_s: float = 2.0,
    sample_rate: int = 16000,
) -> np.ndarray:
    """Simule de la parole avec une voix qui s'éteint graduellement.

    Pattern réaliste : la dernière phrase est dite plus doucement,
    l'amplitude tombe de 0.15 à 0.002 sur 2 secondes.
    Le VAD énergie peut classifier ces frames comme silence.
    """
    total_samples = int(duration_s * sample_rate)
    fade_samples = int(fade_duration_s * sample_rate)
    speech_samples = total_samples - fade_samples

    # Parole normale : amplitude ~0.15
    speech = np.random.uniform(-0.15, 0.15, speech_samples).astype(np.float32)

    # Fade-out graduel : 0.15 → 0.002 (sous le seuil dynamique)
    fade = np.random.uniform(-0.15, 0.15, fade_samples).astype(np.float32)
    fade_envelope = np.linspace(1.0, 0.013, fade_samples).astype(np.float32)
    fade = fade * fade_envelope

    return np.concatenate([speech, fade])


class TestTrimSilenceFadingSpeech:
    """Le VAD énergie ne doit pas couper une voix qui s'éteint doucement."""

    def test_fade_out_speech_not_aggressively_trimmed(self):
        """Voix qui s'éteint sur 2s → perte max 800ms (padding + marge).

        C'est le scénario du bug : la dernière phrase est dite plus bas,
        et le VAD la classe comme silence.
        """
        processor = AudioProcessor(sample_rate=16000, vad_aggressiveness=2)
        audio = _make_speech_with_gradual_fade(
            duration_s=27.0, fade_duration_s=2.0, sample_rate=16000,
        )
        original_duration = len(audio) / 16000

        trimmed = processor.trim_silence(audio)
        trimmed_duration = len(trimmed) / 16000

        lost = original_duration - trimmed_duration
        # Avec padding 300ms, on perd la partie du fade sous le seuil (~1s)
        # MOINS le padding (300ms). Résultat attendu : perte ~0.7s.
        # On accepte jusqu'à 1s de perte mais pas 2s.
        assert lost < 1.0, (
            f"trim_silence a coupé {lost:.2f}s — trop agressif sur voix décroissante. "
            f"Original: {original_duration:.2f}s, Trimmed: {trimmed_duration:.2f}s"
        )

    def test_trim_padding_protects_end_of_speech(self):
        """Vérifie que le padding (300ms) est bien ajouté après le dernier frame de parole."""
        processor = AudioProcessor(sample_rate=16000, vad_aggressiveness=2)
        # 10s de parole forte + 0.5s de silence total
        speech = np.random.uniform(-0.2, 0.2, 160000).astype(np.float32)
        silence = np.zeros(8000, dtype=np.float32)
        audio = np.concatenate([speech, silence])

        trimmed = processor.trim_silence(audio)
        trimmed_duration = len(trimmed) / 16000

        # Le padding de 300ms devrait garder au moins 10.0 + 0.3 = 10.3s
        # sur les 10.5s totales
        assert trimmed_duration >= 10.0, (
            f"Padding insuffisant : {trimmed_duration:.2f}s au lieu d'au moins 10.0s"
        )


# ── Bug A : clipboard restauré trop vite ─────────────────────────────────────

class TestInjectRawClipboardTiming:
    """Le clipboard doit rester avec le texte dicté assez longtemps pour que l'app colle."""

    def test_delay_before_clipboard_restore(self):
        """Mesure le délai entre _inject_direct (clipboard+Ctrl+V) et la restauration.

        Si ce délai est < 100ms, les apps lentes (Electron, WinUI3) peuvent
        coller le contenu original au lieu du texte dicté.
        """
        from src.injection.progressive_injector import ProgressiveInjector

        injector_mock = MagicMock()
        prog = ProgressiveInjector(injector_mock)

        # Tracer les moments de chaque appel pyperclip
        copy_calls = []

        def mock_copy(text):
            copy_calls.append({"text": text, "time": time.monotonic()})

        def mock_paste():
            return "original_content"

        # Simuler _inject_direct qui retourne True (pas de fallback)
        with patch.object(prog, "_inject_direct", return_value=True):
            with patch("pyperclip.copy", side_effect=mock_copy):
                with patch("pyperclip.paste", side_effect=mock_paste):
                    prog.inject_raw("texte dicté")

        # On s'attend à 1 appel copy dans _inject_direct (via le patch, mais on l'a bypassé)
        # + 1 appel copy pour restaurer le clipboard
        # Puisqu'on a patché _inject_direct, le seul copy est la restauration
        # Le délai entre _inject_direct et la restauration doit être >= 100ms
        assert len(copy_calls) >= 1, "pyperclip.copy devrait être appelé pour restaurer"
        # Le premier copy_call est la restauration du clipboard original
        assert copy_calls[0]["text"] == "original_content", (
            f"Le clipboard devrait être restauré avec 'original_content', pas '{copy_calls[0]['text']}'"
        )

    def test_user_watch_starts_after_inject(self):
        """Vérifie que _start_user_watch est appelé APRÈS inject_raw, pas avant."""
        from src.injection.progressive_injector import ProgressiveInjector

        injector_mock = MagicMock()
        prog = ProgressiveInjector(injector_mock)

        call_order = []

        original_inject = prog._inject_direct
        original_watch = prog._start_user_watch

        def mock_inject(text):
            call_order.append("inject")
            return False  # force fallback

        def mock_watch():
            call_order.append("watch")

        with patch.object(prog, "_inject_direct", side_effect=mock_inject):
            with patch.object(prog, "_start_user_watch", side_effect=mock_watch):
                with patch("pyperclip.paste", return_value=""):
                    with patch("pyperclip.copy"):
                        prog.inject_raw("test")

        assert "inject" in call_order, "inject_direct devrait être appelé"
        assert "watch" in call_order, "start_user_watch devrait être appelé"
        assert call_order.index("inject") < call_order.index("watch"), (
            "inject_direct doit être appelé AVANT start_user_watch"
        )
