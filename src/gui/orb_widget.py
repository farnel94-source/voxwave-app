"""OrbWidget — QPainter-based floating orb for VoxWave.

Replaces the QWebEngineView-based waveform_widget.py.
Draws the orb (logo, aura, text, animations) using native QPainter.
Transparent background via WA_TranslucentBackground (no Chromium dependency).
"""

import logging
import math
import sys
import time
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot, QPointF, QRectF
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath,
    QPen, QPixmap, QRadialGradient,
)
from PySide6.QtWidgets import QApplication, QWidget

logger = logging.getLogger(__name__)

# --- Constants ---
WIDGET_WIDTH = 300
WIDGET_HEIGHT = 116
ERROR_DISPLAY_MS = 3000
ANIM_INTERVAL_MS = 33    # ~30 FPS
AMPLITUDE_INTERVAL_MS = 50

# Logo
LOGO_SIZE = 44
LOGO_RADIUS = LOGO_SIZE / 2  # 22

# Aura
AURA_SIZE = 90  # QPixmap size for aura rendering
CORE_BASE_RADIUS = 26
PARTICLE_COUNT = 15

# Drag threshold
DRAG_THRESHOLD = 5


def _restore_foreground_window() -> Optional[Callable]:
    """Capture la fenetre active et retourne une fonction pour la restaurer."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return None

        def restore():
            try:
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
        return restore
    except Exception:
        return None


class OrbWidget(QWidget):
    """Widget orbe flottant dessine en QPainter natif."""

    # Signals thread-safe (meme API que WaveformWidget)
    sig_show_recording = Signal()
    sig_show_processing = Signal()
    sig_show_idle = Signal()
    sig_show_error = Signal()
    sig_update_step = Signal(str)
    sig_set_error_text = Signal(str)
    sig_show_preview = Signal(str)
    sig_hide_widget = Signal()
    sig_hide_widget_delayed = Signal(str)

    def __init__(
        self,
        on_start: Callable,
        on_stop: Callable,
        on_settings: Callable,
        on_quit: Callable,
        capture: Optional[object] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._capture = capture

        # State
        self._state = "idle"
        self._amplitude = 0.0
        self._smoothed_volume = 0.0
        self._target_amplitude = 0.0
        self._anim_time = 0.0
        self._anim_start = time.monotonic()
        self._timer_seconds = 0
        self._timer_start = 0.0
        self._step_text = ""
        self._error_text = ""
        self._preview_text = ""

        # Animations
        self._success_start = 0.0
        self._error_start = 0.0
        self._expand_progress = 0.0  # 0.0 (collapsed) -> 1.0 (expanded)

        # Drag
        self._drag_start_pos = None
        self._drag_started = False
        self._mouse_press_pos = None
        self._saved_restore: Optional[Callable] = None

        # Cache
        self._cached_dpr = 0.0
        self._shadow_cache: Optional[QPixmap] = None

        self._setup_window()
        self._setup_timers()
        self._connect_signals()
        self._build_static_cache()
        self.show()

    # ================================================================
    # Window setup
    # ================================================================

    def _setup_window(self) -> None:
        """Configure la fenetre frameless, always-on-top, transparente."""
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(WIDGET_WIDTH, WIDGET_HEIGHT)
        self._center_bottom()

    def _center_bottom(self) -> None:
        """Positionne le widget en bas-centre de l'ecran."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - WIDGET_WIDTH) // 2
            y = geo.y() + geo.height() - WIDGET_HEIGHT - 40
            self.move(x, y)

    def _setup_timers(self) -> None:
        """Configure les timers d'animation et d'amplitude."""
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(ANIM_INTERVAL_MS)
        self._anim_timer.timeout.connect(self._animation_tick)
        self._anim_timer.start()

        self._amplitude_timer = QTimer(self)
        self._amplitude_timer.setInterval(AMPLITUDE_INTERVAL_MS)
        self._amplitude_timer.timeout.connect(self._amplitude_tick)

    def _connect_signals(self) -> None:
        """Connecte les signals pour les appels thread-safe."""
        self.sig_show_recording.connect(self._do_show_recording)
        self.sig_show_processing.connect(self._do_show_processing)
        self.sig_show_idle.connect(self._do_show_idle)
        self.sig_show_error.connect(self._do_show_error)
        self.sig_update_step.connect(self._do_update_step)
        self.sig_set_error_text.connect(self._do_set_error_text)
        self.sig_show_preview.connect(self._do_show_preview)
        self.sig_hide_widget.connect(self.hide)
        self.sig_hide_widget_delayed.connect(self._do_hide_delayed)

    # ================================================================
    # Static cache (shadow + edge ring at amplitude=0)
    # ================================================================

    def _build_static_cache(self) -> None:
        """Pre-rend les couches statiques de l'aura dans des QPixmap."""
        dpr = self.devicePixelRatioF()
        self._cached_dpr = dpr
        size = int(AURA_SIZE * dpr)

        # Shadow layer (couche 0)
        shadow = QPixmap(size, size)
        shadow.setDevicePixelRatio(dpr)
        shadow.fill(Qt.transparent)
        p = QPainter(shadow)
        p.setRenderHint(QPainter.Antialiasing)

        # Clip to circle
        clip = QPainterPath()
        clip.addEllipse(QRectF(0, 0, AURA_SIZE, AURA_SIZE))
        p.setClipPath(clip)

        # Radial gradient: black shadow
        center = QPointF(AURA_SIZE / 2, AURA_SIZE / 2)
        grad = QRadialGradient(center, 42)
        grad.setColorAt(0.0, QColor(0, 0, 0, 25))    # 0.10 opacity
        grad.setColorAt(0.6, QColor(0, 0, 0, 13))    # 0.05 opacity
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(0, 0, AURA_SIZE, AURA_SIZE))
        p.end()

        self._shadow_cache = shadow
        logger.debug("Static cache built (DPR=%.1f)", dpr)

    def _invalidate_cache(self) -> None:
        """Invalide le cache si le DPI a change."""
        new_dpr = self.devicePixelRatioF()
        if abs(new_dpr - self._cached_dpr) > 0.01:
            self._build_static_cache()

    # ================================================================
    # Public API (thread-safe)
    # ================================================================

    def show_recording(self) -> None:
        self.sig_show_recording.emit()

    def show_processing(self) -> None:
        self.sig_show_processing.emit()

    def show_idle(self) -> None:
        self.sig_show_idle.emit()

    def show_error(self) -> None:
        self.sig_show_error.emit()

    def set_error_text(self, text: str) -> None:
        self.sig_set_error_text.emit(text)

    def update_step(self, step_text: str) -> None:
        self.sig_update_step.emit(step_text)

    def show_preview(self, text: str) -> None:
        truncated = text[:50] if len(text) > 50 else text
        self.sig_show_preview.emit(truncated)

    def hide_widget(self) -> None:
        self.sig_show_idle.emit()

    def set_capture(self, capture) -> None:
        self._capture = capture

    def ensure_topmost(self) -> None:
        """Re-applique le flag always-on-top via Win32 SetWindowPos."""
        if sys.platform != "win32" or not self.isVisible():
            return
        try:
            import ctypes
            import ctypes.wintypes
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowPos(
                ctypes.wintypes.HWND(hwnd),
                ctypes.wintypes.HWND(-1),  # HWND_TOPMOST
                0, 0, 0, 0,
                0x0002 | 0x0001 | 0x0010,  # SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            )
        except Exception:
            logger.debug("ensure_topmost failed", exc_info=True)

    @property
    def state(self) -> str:
        """Retourne l'etat courant du widget."""
        return self._state

    # ================================================================
    # Internal state handlers (main thread)
    # ================================================================

    @Slot()
    def _do_show_recording(self) -> None:
        self._state = "recording"
        self._timer_start = time.monotonic()
        self._timer_seconds = 0
        self._amplitude_timer.start()
        self.show()
        logger.debug("OrbWidget: -> recording")

    @Slot()
    def _do_show_processing(self) -> None:
        self._state = "processing"
        self._amplitude_timer.stop()
        self._target_amplitude = 0.0
        logger.debug("OrbWidget: -> processing")

    @Slot()
    def _do_show_idle(self) -> None:
        prev = self._state
        self._state = "idle"
        self._amplitude_timer.stop()
        self._target_amplitude = 0.0
        self._preview_text = ""
        if prev == "processing":
            self._success_start = time.monotonic()
        logger.debug("OrbWidget: -> idle")

    @Slot()
    def _do_show_error(self) -> None:
        self._state = "error"
        self._error_start = time.monotonic()
        self._amplitude_timer.stop()
        self._target_amplitude = 0.0
        QTimer.singleShot(ERROR_DISPLAY_MS, self._do_show_idle)
        logger.debug("OrbWidget: -> error")

    @Slot(str)
    def _do_update_step(self, step_text: str) -> None:
        self._step_text = step_text

    @Slot(str)
    def _do_set_error_text(self, text: str) -> None:
        self._error_text = text

    @Slot(str)
    def _do_show_preview(self, text: str) -> None:
        self._preview_text = text.replace("\n", " ")

    @Slot(str)
    def _do_hide_delayed(self) -> None:
        QTimer.singleShot(900, self.hide)

    # ================================================================
    # Animation tick
    # ================================================================

    def _animation_tick(self) -> None:
        """Appele toutes les 33ms (30 FPS). Met a jour l'etat d'animation."""
        now = time.monotonic()
        self._anim_time = now - self._anim_start

        # Smooth amplitude (exponential moving average)
        self._amplitude += (self._target_amplitude - self._amplitude) * 0.12
        self._smoothed_volume += (self._target_amplitude - self._smoothed_volume) * 0.2

        # Timer update
        if self._state == "recording" and self._timer_start > 0:
            self._timer_seconds = int(now - self._timer_start)

        # Expand animation (pill opening/closing)
        target_expand = 1.0 if self._state in ("recording", "processing", "error") else 0.0
        self._expand_progress += (target_expand - self._expand_progress) * 0.15

        self._invalidate_cache()
        self.update()  # Trigger repaint

    def _amplitude_tick(self) -> None:
        """Lit l'amplitude du micro et met a jour la cible."""
        if self._capture:
            raw = getattr(self._capture, "current_amplitude", 0.0)
            self._target_amplitude = min(raw * 4.0, 1.0)

    # ================================================================
    # Animation helpers
    # ================================================================

    def _get_breathe(self) -> float:
        """Retourne la valeur de respiration (0.0 -> 1.0)."""
        period = 1.8 if self._state == "recording" else 3.5
        return math.sin(self._anim_time * 2 * math.pi / period) * 0.5 + 0.5

    def _get_shake_offset(self) -> float:
        """Retourne le decalage horizontal pour l'animation shake (error)."""
        if self._state != "error":
            return 0.0
        elapsed = time.monotonic() - self._error_start
        if elapsed > 0.45:
            return 0.0
        # Keyframes: 0, -3, 3, -2, 2, -1, 1, 0
        keyframes = [0, -3, 3, -2, 2, -1, 1, 0]
        times = [0, 0.06, 0.12, 0.18, 0.24, 0.30, 0.36, 0.45]
        # Find segment
        for i in range(len(times) - 1):
            if elapsed <= times[i + 1]:
                t = (elapsed - times[i]) / (times[i + 1] - times[i])
                return keyframes[i] + (keyframes[i + 1] - keyframes[i]) * t
        return 0.0

    def _get_success_scale(self) -> float:
        """Retourne le scale factor pour l'animation success bounce."""
        elapsed = time.monotonic() - self._success_start
        if elapsed > 0.5 or self._success_start == 0.0:
            return 1.0
        # Keyframes: 1.0, 1.06, 0.98, 1.0
        keyframes = [1.0, 1.06, 0.98, 1.0]
        times = [0, 0.2, 0.35, 0.5]
        for i in range(len(times) - 1):
            if elapsed <= times[i + 1]:
                t = (elapsed - times[i]) / (times[i + 1] - times[i])
                return keyframes[i] + (keyframes[i + 1] - keyframes[i]) * t
        return 1.0

    def _get_dot_offset(self, dot_index: int) -> float:
        """Retourne le decalage vertical pour un dot de processing."""
        cycle = 1.4
        delay = dot_index * 0.14
        phase = ((self._anim_time - delay) % cycle) / cycle
        return -4.0 * max(0.0, math.sin(math.pi * phase))

    # ================================================================
    # Paint — main entry point
    # ================================================================

    def paintEvent(self, event) -> None:
        """Dessine l'orbe complet."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Logo center position
        logo_cx = 58.0  # Left-aligned logo (like orb.html)
        logo_cy = WIDGET_HEIGHT / 2.0

        # Shake offset (error state)
        shake_dx = self._get_shake_offset()
        if shake_dx != 0:
            painter.translate(shake_dx, 0)

        # Success scale
        scale = self._get_success_scale()
        if abs(scale - 1.0) > 0.001:
            painter.translate(logo_cx, logo_cy)
            painter.scale(scale, scale)
            painter.translate(-logo_cx, -logo_cy)

        # Draw layers
        self._paint_aura(painter, logo_cx, logo_cy)
        self._paint_logo(painter, logo_cx, logo_cy)

        # Text (to the right of logo, in the expanded pill area)
        if self._expand_progress > 0.01:
            if self._state == "recording":
                self._paint_timer(painter, logo_cx, logo_cy)
            elif self._state == "processing":
                self._paint_processing(painter, logo_cx, logo_cy)
            elif self._state == "error":
                self._paint_error(painter, logo_cx, logo_cy)

        painter.end()

    # ================================================================
    # Paint — Aura (5 layers)
    # ================================================================

    def _paint_aura(self, painter: QPainter, cx: float, cy: float) -> None:
        """Dessine les 5 couches de l'aura autour du logo."""
        intensity = min(pow(self._smoothed_volume * 2.5, 1.2), 1.5)
        breathe = self._get_breathe()
        is_active = self._state in ("recording", "idle")

        if not is_active and self._state != "idle":
            # No aura in processing/error
            return

        # Aura opacity based on state
        if self._state == "recording":
            base_opacity = 0.6 + intensity * 0.4
        else:
            base_opacity = 0.3 + breathe * 0.15

        dpr = self.devicePixelRatioF()
        aura_pix = QPixmap(int(AURA_SIZE * dpr), int(AURA_SIZE * dpr))
        aura_pix.setDevicePixelRatio(dpr)
        aura_pix.fill(Qt.transparent)

        ap = QPainter(aura_pix)
        ap.setRenderHint(QPainter.Antialiasing)

        # Clip to circle
        clip = QPainterPath()
        clip.addEllipse(QRectF(0, 0, AURA_SIZE, AURA_SIZE))
        ap.setClipPath(clip)

        aura_center = QPointF(AURA_SIZE / 2, AURA_SIZE / 2)

        # Layer 0: Shadow (from cache)
        if self._shadow_cache:
            shadow_opacity = 0.10 + intensity * 0.15
            ap.setOpacity(shadow_opacity)
            ap.drawPixmap(0, 0, self._shadow_cache)
            ap.setOpacity(1.0)

        # Layer 1: Outer aura (dynamic radial gradient)
        outer_radius = CORE_BASE_RADIUS + 20 + breathe * 6 + intensity * 30
        outer_grad = QRadialGradient(aura_center, outer_radius)
        outer_a = int(min(255, (0.15 + intensity * 0.35) * 255))
        outer_grad.setColorAt(0.0, QColor(99, 102, 241, outer_a))      # indigo
        outer_grad.setColorAt(0.5, QColor(59, 130, 246, int(outer_a * 0.6)))  # blue
        outer_grad.setColorAt(1.0, QColor(59, 130, 246, 0))
        ap.setBrush(QBrush(outer_grad))
        ap.setPen(Qt.NoPen)
        ap.drawEllipse(QRectF(0, 0, AURA_SIZE, AURA_SIZE))

        # Layer 2: Core glow (dynamic radial gradient)
        core_radius = CORE_BASE_RADIUS + intensity * 35
        core_grad = QRadialGradient(aura_center, core_radius)
        core_a = int(min(255, (0.2 + intensity * 0.3) * 255))
        core_grad.setColorAt(0.0, QColor(34, 211, 238, core_a))        # cyan
        core_grad.setColorAt(0.5, QColor(59, 130, 246, int(core_a * 0.5)))
        core_grad.setColorAt(1.0, QColor(59, 130, 246, 0))
        ap.setBrush(QBrush(core_grad))
        ap.drawEllipse(QRectF(0, 0, AURA_SIZE, AURA_SIZE))

        # Layer 3: Particles (15 small dots)
        t = self._anim_time
        for i in range(PARTICLE_COUNT):
            angle = (i / PARTICLE_COUNT) * 2 * math.pi + t * 0.5 + i * math.radians(132.5)
            dist = CORE_BASE_RADIUS + math.sin(t * 3 + i * math.radians(54)) * 6 + intensity * 40
            px = aura_center.x() + math.cos(angle) * dist
            py = aura_center.y() + math.sin(angle) * dist
            dot_size = 1.5 + intensity * 1.5
            dot_opacity = int(min(255, (0.2 + intensity * 0.5) * 255))
            ap.setBrush(QBrush(QColor(147, 197, 253, dot_opacity)))
            ap.setPen(Qt.NoPen)
            ap.drawEllipse(QPointF(px, py), dot_size, dot_size)

        # Layer 4: Edge ring
        edge_radius = outer_radius - 1
        if edge_radius > 5:
            ap.setBrush(Qt.NoBrush)
            ap.setPen(QPen(QColor(0, 0, 0, 38), 1.5))  # rgba(0,0,0,0.15)
            ap.drawEllipse(aura_center, edge_radius, edge_radius)

        ap.end()

        # Composite aura pixmap centered on logo
        ax = cx - AURA_SIZE / 2
        ay = cy - AURA_SIZE / 2
        painter.setOpacity(base_opacity)
        painter.drawPixmap(QPointF(ax, ay), aura_pix)
        painter.setOpacity(1.0)

    # ================================================================
    # Paint — Logo (circle + SVG "vw" path)
    # ================================================================

    def _paint_logo(self, painter: QPainter, cx: float, cy: float) -> None:
        """Dessine le cercle du logo et le path SVG 'vw'."""
        # Glow (drop-shadow behind circle)
        self._paint_glow(painter, cx, cy)

        # Circle background
        painter.setBrush(QBrush(QColor(15, 23, 42, 153)))  # rgba(15,23,42,0.6)

        # Border color per state
        if self._state == "recording":
            border_color = QColor(59, 130, 246, 128)   # blue 0.5
        elif self._state == "error":
            border_color = QColor(239, 68, 68, 128)    # red 0.5
        else:
            border_color = QColor(148, 163, 184, 77)   # slate 0.3

        painter.setPen(QPen(border_color, 1))
        painter.drawEllipse(QPointF(cx, cy), LOGO_RADIUS, LOGO_RADIUS)

        # SVG "vw" path
        self._paint_vw_path(painter, cx, cy)

    def _paint_glow(self, painter: QPainter, cx: float, cy: float) -> None:
        """Dessine le glow (drop-shadow) derriere le cercle logo."""
        now = time.monotonic()
        breathe = self._get_breathe()

        # Glow parameters per state
        if self._state == "error":
            glow_color = QColor(239, 68, 68, int(0.8 * 255))
            glow_extra = 4
        elif self._success_start > 0 and (now - self._success_start) < 0.5:
            # Success flash (green)
            progress = (now - self._success_start) / 0.5
            alpha = int((1.0 - progress) * 0.9 * 255)
            glow_color = QColor(74, 222, 128, alpha)
            glow_extra = 6
        elif self._state == "recording":
            alpha = int((0.2 + breathe * 0.2) * 255)
            glow_color = QColor(255, 255, 255, alpha)
            glow_extra = 3 + breathe * 3
        else:
            # idle
            alpha = int((0.1 + breathe * 0.1) * 255)
            glow_color = QColor(255, 255, 255, alpha)
            glow_extra = 2 + breathe * 2

        painter.setBrush(QBrush(glow_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), LOGO_RADIUS + glow_extra, LOGO_RADIUS + glow_extra)

    def _paint_vw_path(self, painter: QPainter, cx: float, cy: float) -> None:
        """Dessine le path SVG 'vw' a l'interieur du cercle logo."""
        # Scale: viewBox 100x100 -> 28x28px (factor 0.28)
        scale = 0.28
        # Offset to center the 28x28 path in the 44x44 circle
        ox = cx - 14  # 28/2 = 14
        oy = cy - 14

        path = QPainterPath()
        # M(20,45) then 6 cubicTo calls
        path.moveTo(ox + 20 * scale, oy + 45 * scale)
        path.cubicTo(
            ox + 22 * scale, oy + 45 * scale,
            ox + 26 * scale, oy + 60 * scale,
            ox + 32 * scale, oy + 60 * scale,
        )
        path.cubicTo(
            ox + 38 * scale, oy + 60 * scale,
            ox + 38 * scale, oy + 40 * scale,
            ox + 42 * scale, oy + 40 * scale,
        )
        path.cubicTo(
            ox + 46 * scale, oy + 40 * scale,
            ox + 46 * scale, oy + 58 * scale,
            ox + 50 * scale, oy + 58 * scale,
        )
        path.cubicTo(
            ox + 54 * scale, oy + 58 * scale,
            ox + 54 * scale, oy + 40 * scale,
            ox + 58 * scale, oy + 40 * scale,
        )
        path.cubicTo(
            ox + 62 * scale, oy + 40 * scale,
            ox + 62 * scale, oy + 58 * scale,
            ox + 66 * scale, oy + 58 * scale,
        )
        path.cubicTo(
            ox + 70 * scale, oy + 58 * scale,
            ox + 74 * scale, oy + 42 * scale,
            ox + 80 * scale, oy + 42 * scale,
        )

        # Stroke gradient (white -> gray)
        grad = QLinearGradient(
            QPointF(ox + 20 * scale, oy + 45 * scale),
            QPointF(ox + 80 * scale, oy + 45 * scale),
        )
        grad.setColorAt(0.0, QColor(255, 255, 255, 230))  # rgba(255,255,255,0.9)
        grad.setColorAt(1.0, QColor(200, 200, 210, 179))  # rgba(200,200,210,0.7)

        pen = QPen(QBrush(grad), 3.5 * scale)  # ~1.0px
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        painter.drawPath(path)

    # ================================================================
    # Paint — Text (timer, processing, error)
    # ================================================================

    def _paint_timer(self, painter: QPainter, cx: float, cy: float) -> None:
        """Dessine le timer MM:SS pendant le recording."""
        mins = self._timer_seconds // 60
        secs = self._timer_seconds % 60
        text = f"{mins:02d}:{secs:02d}"

        font = QFont("Segoe UI", 12)
        font.setStyleStrategy(QFont.PreferAntialias)
        painter.setFont(font)

        # Position: to the right of logo circle
        text_x = cx + LOGO_RADIUS + 12
        text_y = cy + 5  # Vertically centered

        opacity = min(1.0, self._expand_progress * 2)
        painter.setOpacity(opacity * 0.75)
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(QPointF(text_x, text_y), text)
        painter.setOpacity(1.0)

    def _paint_processing(self, painter: QPainter, cx: float, cy: float) -> None:
        """Dessine le texte de processing + 3 dots animes."""
        text_x = cx + LOGO_RADIUS + 12
        text_y = cy + 5

        opacity = min(1.0, self._expand_progress * 2)

        # Show preview text if available, otherwise step text
        display_text = self._preview_text if self._preview_text else self._step_text
        if not display_text:
            display_text = "Traitement..."

        font = QFont("Segoe UI", 12)
        painter.setFont(font)
        painter.setOpacity(opacity * 0.45)
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(QPointF(text_x, text_y), display_text)

        # Bouncing dots (only if no preview)
        if not self._preview_text:
            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(display_text)
            dot_x_start = text_x + text_width + 6

            painter.setOpacity(opacity * 0.7)
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.setPen(Qt.NoPen)

            for i in range(3):
                dy = self._get_dot_offset(i)
                dot_cx = dot_x_start + i * 8
                dot_cy = text_y - 3 + dy
                painter.drawEllipse(QPointF(dot_cx, dot_cy), 1.5, 1.5)

        painter.setOpacity(1.0)

    def _paint_error(self, painter: QPainter, cx: float, cy: float) -> None:
        """Dessine le texte d'erreur en rouge."""
        text_x = cx + LOGO_RADIUS + 12
        text_y = cy + 5

        opacity = min(1.0, self._expand_progress * 2)
        display_text = self._error_text if self._error_text else "Erreur"

        font = QFont("Segoe UI", 12)
        font.setBold(True)
        painter.setFont(font)
        painter.setOpacity(opacity)
        painter.setPen(QPen(QColor(248, 113, 113)))  # #F87171
        painter.drawText(QPointF(text_x, text_y), display_text)
        painter.setOpacity(1.0)

    # ================================================================
    # Mouse interactions
    # ================================================================

    def mousePressEvent(self, event) -> None:
        """Debut du drag ou du clic."""
        if event.button() == Qt.LeftButton:
            self._mouse_press_pos = event.globalPosition().toPoint()
            self._drag_start_pos = self.pos()
            self._drag_started = False
            # Save foreground window for focus restoration
            self._saved_restore = _restore_foreground_window()

    def mouseMoveEvent(self, event) -> None:
        """Drag si le deplacement depasse le seuil de 5px."""
        if self._mouse_press_pos is None:
            return
        current = event.globalPosition().toPoint()
        delta = current - self._mouse_press_pos
        dist = (delta.x() ** 2 + delta.y() ** 2) ** 0.5

        if dist >= DRAG_THRESHOLD:
            self._drag_started = True
            new_pos = self._drag_start_pos + delta
            self.move(new_pos)

    def mouseReleaseEvent(self, event) -> None:
        """Fin du drag ou clic (start/stop)."""
        if event.button() == Qt.LeftButton and not self._drag_started:
            # Click — start or stop based on state
            if self._state == "idle":
                if self._on_start:
                    self._on_start()
                # Restore foreground window
                if self._saved_restore:
                    QTimer.singleShot(100, self._saved_restore)
            elif self._state == "recording":
                if self._on_stop:
                    self._on_stop()
                if self._saved_restore:
                    QTimer.singleShot(100, self._saved_restore)
                    self._saved_restore = None

        self._mouse_press_pos = None
        self._drag_started = False

    def contextMenuEvent(self, event) -> None:
        """Clic droit → ouvrir les parametres."""
        if self._on_settings:
            self._on_settings()

    def moveEvent(self, event) -> None:
        """Detecte un changement de DPI quand le widget bouge entre ecrans."""
        super().moveEvent(event)
        self._invalidate_cache()
