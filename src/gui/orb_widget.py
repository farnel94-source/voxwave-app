"""OrbWidget — QPainter-based floating orb for VoxWave.

Replaces the QWebEngineView-based waveform_widget.py.
Draws the orb (logo, aura, text, animations) using native QPainter.
Transparency via Win32 UpdateLayeredWindow (bypasses PySide6 6.11 bug).
On Linux, uses WA_TranslucentBackground (works fine).
"""

import ctypes
import ctypes.wintypes
import logging
import math
import sys
import time
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot, QPointF, QRectF
from PySide6.QtGui import (
    QBrush, QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath,
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

# Win32 constants
_IS_WIN32 = sys.platform == "win32"
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0
AC_SRC_ALPHA = 1


# --- Win32 structures (module-level, definis une seule fois) ---

if _IS_WIN32:
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class SIZE(ctypes.Structure):
        _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]

    class BLENDFUNCTION(ctypes.Structure):
        _fields_ = [
            ("BlendOp", ctypes.c_byte),
            ("BlendFlags", ctypes.c_byte),
            ("SourceConstantAlpha", ctypes.c_byte),
            ("AlphaFormat", ctypes.c_byte),
        ]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", ctypes.c_uint),
            ("biWidth", ctypes.c_int),
            ("biHeight", ctypes.c_int),
            ("biPlanes", ctypes.c_ushort),
            ("biBitCount", ctypes.c_ushort),
            ("biCompression", ctypes.c_uint),
            ("biSizeImage", ctypes.c_uint),
            ("biXPelsPerMeter", ctypes.c_int),
            ("biYPelsPerMeter", ctypes.c_int),
            ("biClrUsed", ctypes.c_uint),
            ("biClrImportant", ctypes.c_uint),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [
            ("bmiHeader", BITMAPINFOHEADER),
            ("bmiColors", ctypes.c_uint * 3),
        ]


def _restore_foreground_window() -> Optional[Callable]:
    """Capture la fenetre active et retourne une fonction pour la restaurer."""
    if not _IS_WIN32:
        return None
    try:
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


def _update_layered_window(hwnd: int, image: QImage) -> bool:
    """Envoie un QImage a Windows via UpdateLayeredWindow (per-pixel alpha)."""
    w, h = image.width(), image.height()
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h  # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0

    bits = ctypes.c_void_p()
    hbitmap = gdi32.CreateDIBSection(
        hdc_mem, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0
    )
    if not hbitmap:
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)
        return False

    raw = bytes(image.constBits())
    ctypes.memmove(bits, raw, w * h * 4)

    old_bmp = gdi32.SelectObject(hdc_mem, hbitmap)

    pt_src = POINT(0, 0)
    size = SIZE(w, h)
    blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)

    result = user32.UpdateLayeredWindow(
        hwnd, hdc_screen, None, ctypes.byref(size),
        hdc_mem, ctypes.byref(pt_src), 0,
        ctypes.byref(blend), ULW_ALPHA,
    )

    gdi32.SelectObject(hdc_mem, old_bmp)
    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)

    return bool(result)


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

        # Win32 layered window
        self._use_layered = _IS_WIN32
        self._hwnd = 0

        self._setup_window()
        self._setup_timers()
        self._connect_signals()
        self._build_static_cache()
        self.show()

        # Win32: activer WS_EX_LAYERED apres show() pour que le HWND existe
        if self._use_layered:
            self._setup_layered_window()
            self._render_layered()

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
        if not self._use_layered:
            # Linux: utiliser la transparence Qt native (fonctionne bien)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(WIDGET_WIDTH, WIDGET_HEIGHT)
        self._center_bottom()

    def _setup_layered_window(self) -> None:
        """Active WS_EX_LAYERED + desactive DWM sur Windows."""
        try:
            self._hwnd = int(self.winId())

            # WS_EX_LAYERED
            style = ctypes.windll.user32.GetWindowLongW(self._hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                self._hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED
            )

            # Desactiver coins arrondis Windows 11
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            val = ctypes.c_int(1)  # DWMWCP_DONOTROUND
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                self._hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(val), ctypes.sizeof(val),
            )

            # Desactiver backdrop DWM
            DWMWA_SYSTEMBACKDROP_TYPE = 38
            val2 = ctypes.c_int(1)  # DWMSBT_NONE
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                self._hwnd, DWMWA_SYSTEMBACKDROP_TYPE,
                ctypes.byref(val2), ctypes.sizeof(val2),
            )

            # Desactiver NC rendering DWM
            DWMWA_NCRENDERING_POLICY = 2
            val3 = ctypes.c_int(1)  # DWMNCRP_DISABLED
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                self._hwnd, DWMWA_NCRENDERING_POLICY,
                ctypes.byref(val3), ctypes.sizeof(val3),
            )

            logger.debug("Layered window setup OK (HWND=%s)", self._hwnd)
        except Exception:
            logger.warning("Layered window setup failed, falling back to Qt", exc_info=True)
            self._use_layered = False
            self.setAttribute(Qt.WA_TranslucentBackground, True)

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
    # Static cache (shadow layer)
    # ================================================================

    def _build_static_cache(self) -> None:
        """Pre-rend les couches statiques de l'aura dans des QPixmap."""
        dpr = self.devicePixelRatioF()
        self._cached_dpr = dpr
        size = int(AURA_SIZE * dpr)

        shadow = QPixmap(size, size)
        shadow.setDevicePixelRatio(dpr)
        shadow.fill(Qt.transparent)
        p = QPainter(shadow)
        p.setRenderHint(QPainter.Antialiasing)

        clip = QPainterPath()
        clip.addEllipse(QRectF(0, 0, AURA_SIZE, AURA_SIZE))
        p.setClipPath(clip)

        center = QPointF(AURA_SIZE / 2, AURA_SIZE / 2)
        grad = QRadialGradient(center, 42)
        grad.setColorAt(0.0, QColor(0, 0, 0, 25))
        grad.setColorAt(0.6, QColor(0, 0, 0, 13))
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
        if not _IS_WIN32 or not self.isVisible():
            return
        try:
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowPos(
                ctypes.wintypes.HWND(hwnd),
                ctypes.wintypes.HWND(-1),  # HWND_TOPMOST
                0, 0, 0, 0,
                0x0002 | 0x0001 | 0x0010,
            )
        except Exception:
            logger.debug("ensure_topmost failed", exc_info=True)

    @property
    def state(self) -> str:
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
        """Appele toutes les 33ms (30 FPS)."""
        now = time.monotonic()
        self._anim_time = now - self._anim_start

        self._amplitude += (self._target_amplitude - self._amplitude) * 0.12
        self._smoothed_volume += (self._target_amplitude - self._smoothed_volume) * 0.2

        if self._state == "recording" and self._timer_start > 0:
            self._timer_seconds = int(now - self._timer_start)

        target_expand = 1.0 if self._state in ("recording", "processing", "error") else 0.0
        self._expand_progress += (target_expand - self._expand_progress) * 0.15

        self._invalidate_cache()

        if self._use_layered:
            self._render_layered()
        else:
            self.update()

    def _amplitude_tick(self) -> None:
        if self._capture:
            raw = getattr(self._capture, "current_amplitude", 0.0)
            self._target_amplitude = min(raw * 4.0, 1.0)

    # ================================================================
    # Animation helpers
    # ================================================================

    def _get_breathe(self) -> float:
        # Original orb.html: sin(time * 2) pour idle (~3.14s period)
        if self._state == "recording":
            return math.sin(self._anim_time * 2 * math.pi / 1.8) * 0.5 + 0.5
        return math.sin(self._anim_time * 2) * 0.5 + 0.5

    def _get_shake_offset(self) -> float:
        if self._state != "error":
            return 0.0
        elapsed = time.monotonic() - self._error_start
        if elapsed > 0.45:
            return 0.0
        keyframes = [0, -3, 3, -2, 2, -1, 1, 0]
        times = [0, 0.06, 0.12, 0.18, 0.24, 0.30, 0.36, 0.45]
        for i in range(len(times) - 1):
            if elapsed <= times[i + 1]:
                t = (elapsed - times[i]) / (times[i + 1] - times[i])
                return keyframes[i] + (keyframes[i + 1] - keyframes[i]) * t
        return 0.0

    def _get_success_scale(self) -> float:
        elapsed = time.monotonic() - self._success_start
        if elapsed > 0.5 or self._success_start == 0.0:
            return 1.0
        keyframes = [1.0, 1.06, 0.98, 1.0]
        times = [0, 0.2, 0.35, 0.5]
        for i in range(len(times) - 1):
            if elapsed <= times[i + 1]:
                t = (elapsed - times[i]) / (times[i + 1] - times[i])
                return keyframes[i] + (keyframes[i + 1] - keyframes[i]) * t
        return 1.0

    def _get_dot_offset(self, dot_index: int) -> float:
        cycle = 1.4
        delay = dot_index * 0.14
        phase = ((self._anim_time - delay) % cycle) / cycle
        return -4.0 * max(0.0, math.sin(math.pi * phase))

    # ================================================================
    # Render — layered window (Windows) or paintEvent (Linux)
    # ================================================================

    def _render_layered(self) -> None:
        """Rend tout dans un QImage et l'envoie via UpdateLayeredWindow."""
        if not self._hwnd or not self.isVisible():
            return

        # Tenir compte du DPR (scaling Windows 125%/150%/200%)
        dpr = self.devicePixelRatioF()
        pw = int(WIDGET_WIDTH * dpr)
        ph = int(WIDGET_HEIGHT * dpr)

        image = QImage(pw, ph, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.scale(dpr, dpr)  # Dessiner en coordonnees logiques
        self._paint_all(painter)
        painter.end()

        _update_layered_window(self._hwnd, image)

    def paintEvent(self, event) -> None:
        """Fallback pour Linux (WA_TranslucentBackground fonctionne)."""
        if self._use_layered:
            return  # Sur Windows, on utilise _render_layered
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        self._paint_all(painter)
        painter.end()

    def _paint_linux_background(self, painter: QPainter) -> None:
        """Fond opaque arrondi pour Linux (fallback sans compositeur)."""
        bg = QColor(20, 20, 30, 240)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg))
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, WIDGET_WIDTH, WIDGET_HEIGHT), 20, 20)
        painter.drawPath(path)

    def _paint_all(self, painter: QPainter) -> None:
        """Dessine l'orbe complet dans le painter donne."""
        if not _IS_WIN32:
            self._paint_linux_background(painter)

        logo_cx = 58.0
        logo_cy = WIDGET_HEIGHT / 2.0

        shake_dx = self._get_shake_offset()
        if shake_dx != 0:
            painter.translate(shake_dx, 0)

        scale = self._get_success_scale()
        if abs(scale - 1.0) > 0.001:
            painter.translate(logo_cx, logo_cy)
            painter.scale(scale, scale)
            painter.translate(-logo_cx, -logo_cy)

        self._paint_aura(painter, logo_cx, logo_cy)
        self._paint_logo(painter, logo_cx, logo_cy)

        if self._expand_progress > 0.01:
            if self._state == "recording":
                self._paint_timer(painter, logo_cx, logo_cy)
            elif self._state == "processing":
                self._paint_processing(painter, logo_cx, logo_cy)
            elif self._state == "error":
                self._paint_error(painter, logo_cx, logo_cy)

    # ================================================================
    # Paint — Aura (5 layers)
    # ================================================================

    def _paint_aura(self, painter: QPainter, cx: float, cy: float) -> None:
        intensity = min(pow(self._smoothed_volume * 2.5, 1.2), 1.5)
        breathe = self._get_breathe()

        # Aura uniquement en recording (comme orb.html original)
        # En idle, seul le glow blanc du logo pulse (dans _paint_glow)
        if self._state != "recording":
            return

        # Dessiner directement sur le painter (pas de base_opacity global)
        # pour matcher le rendu de orb.html qui dessine chaque couche independamment
        aura_center = QPointF(cx, cy)

        # Layer 0: Shadow (cercle de contraste pour fond blanc)
        shadow_radius = CORE_BASE_RADIUS + 5 + intensity * 15
        shadow_grad = QRadialGradient(aura_center, shadow_radius)
        shadow_grad.setFocalRadius(CORE_BASE_RADIUS * 0.5)
        sa0 = int(min(255, (0.10 + intensity * 0.15) * 255))
        sa1 = int(min(255, (0.05 + intensity * 0.08) * 255))
        shadow_grad.setColorAt(0.0, QColor(0, 0, 0, sa0))
        shadow_grad.setColorAt(0.6, QColor(0, 0, 0, sa1))
        shadow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(shadow_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(aura_center, shadow_radius, shadow_radius)

        # Layer 1: Outer aura (valeurs orb.html exactes)
        outer_radius = CORE_BASE_RADIUS + 8 + breathe * 4 + intensity * 20
        outer_grad = QRadialGradient(aura_center, outer_radius)
        outer_grad.setFocalRadius(CORE_BASE_RADIUS)
        oa0 = int(min(255, (0.08 + intensity * 0.45) * 255))
        oa1 = int(min(255, (0.04 + intensity * 0.25) * 255))
        outer_grad.setColorAt(0.0, QColor(99, 102, 241, oa0))
        outer_grad.setColorAt(0.5, QColor(59, 130, 246, oa1))
        outer_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(outer_grad))
        painter.drawEllipse(aura_center, outer_radius, outer_radius)

        # Layer 2: Core glow (valeurs orb.html exactes)
        core_radius = CORE_BASE_RADIUS + intensity * 35
        core_grad = QRadialGradient(aura_center, core_radius)
        ca0 = int(min(255, (0.4 + intensity * 0.6) * 255))
        ca1 = int(min(255, (0.15 + intensity * 0.5) * 255))
        core_grad.setColorAt(0.0, QColor(34, 211, 238, ca0))
        core_grad.setColorAt(0.6, QColor(59, 130, 246, ca1))
        core_grad.setColorAt(1.0, QColor(59, 130, 246, 0))
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(aura_center, core_radius, core_radius)

        # Layer 3: Particles (valeurs orb.html exactes)
        t = self._anim_time
        for i in range(PARTICLE_COUNT):
            angle = (i / PARTICLE_COUNT) * 2 * math.pi + t * 0.5 + i * 132.5
            dist = CORE_BASE_RADIUS + math.sin(t * 3 + i * 54) * 6 + intensity * 40
            px = cx + math.cos(angle) * dist
            py = cy + math.sin(angle) * dist
            dot_size = 1.5 + intensity * 1.5
            dot_alpha = 0.2 + intensity * 0.7 + math.sin(t * 4 + i * 27) * 0.15
            dot_alpha = max(0.0, min(1.0, dot_alpha))
            painter.setBrush(QBrush(QColor(147, 197, 253, int(dot_alpha * 255))))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(px, py), dot_size, dot_size)

        # Layer 4: Edge ring
        edge_radius = outer_radius - 1
        if edge_radius > 5:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(0, 0, 0, 38), 1.5))
            painter.drawEllipse(aura_center, edge_radius, edge_radius)

    # ================================================================
    # Paint — Logo
    # ================================================================

    def _paint_logo(self, painter: QPainter, cx: float, cy: float) -> None:
        self._paint_glow(painter, cx, cy)

        painter.setBrush(QBrush(QColor(15, 23, 42, 153)))

        if self._state == "recording":
            border_color = QColor(59, 130, 246, 128)
        elif self._state == "error":
            border_color = QColor(239, 68, 68, 128)
        else:
            border_color = QColor(120, 130, 145, 160)

        painter.setPen(QPen(border_color, 1.5))
        painter.drawEllipse(QPointF(cx, cy), LOGO_RADIUS, LOGO_RADIUS)
        self._paint_vw_path(painter, cx, cy)

    def _paint_glow(self, painter: QPainter, cx: float, cy: float) -> None:
        """Glow subtil derriere le logo (simule CSS drop-shadow)."""
        now = time.monotonic()
        breathe = self._get_breathe()

        # Success flash et error : cercle SOLIDE bien visible
        if self._success_start > 0 and (now - self._success_start) < 0.5:
            progress = (now - self._success_start) / 0.5
            alpha = int((1.0 - progress) * 0.9 * 255)
            painter.setBrush(QBrush(QColor(74, 222, 128, alpha)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(cx, cy), LOGO_RADIUS + 6, LOGO_RADIUS + 6)
            return

        if self._state == "error":
            painter.setBrush(QBrush(QColor(239, 68, 68, int(0.7 * 255))))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(cx, cy), LOGO_RADIUS + 4, LOGO_RADIUS + 4)
            return

        # Idle / recording : pas de glow supplementaire
        return

    def _paint_vw_path(self, painter: QPainter, cx: float, cy: float) -> None:
        scale = 0.28
        ox = cx - 14
        oy = cy - 14

        path = QPainterPath()
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

        grad = QLinearGradient(
            QPointF(ox + 20 * scale, oy + 45 * scale),
            QPointF(ox + 80 * scale, oy + 45 * scale),
        )
        grad.setColorAt(0.0, QColor(255, 255, 255, 230))
        grad.setColorAt(1.0, QColor(200, 200, 210, 179))

        pen = QPen(QBrush(grad), 3.5 * scale)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        painter.drawPath(path)

    # ================================================================
    # Paint — Text
    # ================================================================

    def _paint_timer(self, painter: QPainter, cx: float, cy: float) -> None:
        mins = self._timer_seconds // 60
        secs = self._timer_seconds % 60
        text = f"{mins:02d}:{secs:02d}"

        font = QFont("Segoe UI", 12)
        font.setStyleStrategy(QFont.PreferAntialias)
        painter.setFont(font)

        text_x = cx + LOGO_RADIUS + 12
        text_y = cy + 5

        opacity = min(1.0, self._expand_progress * 2)
        painter.setOpacity(opacity * 0.75)
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(QPointF(text_x, text_y), text)
        painter.setOpacity(1.0)

    def _paint_processing(self, painter: QPainter, cx: float, cy: float) -> None:
        text_x = cx + LOGO_RADIUS + 12
        text_y = cy + 5
        opacity = min(1.0, self._expand_progress * 2)

        display_text = self._preview_text if self._preview_text else self._step_text
        if not display_text:
            display_text = "Traitement..."

        font = QFont("Segoe UI", 12)
        painter.setFont(font)
        painter.setOpacity(opacity * 0.45)
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(QPointF(text_x, text_y), display_text)

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
        text_x = cx + LOGO_RADIUS + 12
        text_y = cy + 5
        opacity = min(1.0, self._expand_progress * 2)

        display_text = self._error_text if self._error_text else "Erreur"

        font = QFont("Segoe UI", 12)
        font.setBold(True)
        painter.setFont(font)
        painter.setOpacity(opacity)
        painter.setPen(QPen(QColor(248, 113, 113)))
        painter.drawText(QPointF(text_x, text_y), display_text)
        painter.setOpacity(1.0)

    # ================================================================
    # Mouse interactions
    # ================================================================

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._mouse_press_pos = event.globalPosition().toPoint()
            self._drag_start_pos = self.pos()
            self._drag_started = False
            self._saved_restore = _restore_foreground_window()

    def mouseMoveEvent(self, event) -> None:
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
        if event.button() == Qt.LeftButton and not self._drag_started:
            if self._state == "idle":
                if self._on_start:
                    self._on_start()
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
        if self._on_settings:
            self._on_settings()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self._invalidate_cache()
