"""Generation d'icones dynamiques pour le system tray."""

import logging
from typing import Literal

from PIL import Image, ImageDraw
from PySide6.QtGui import QIcon, QImage, QPixmap

logger = logging.getLogger(__name__)

IconState = Literal["idle", "recording", "processing", "error"]

# Couleurs par etat (pour le badge indicateur)
STATE_COLORS: dict[str, str] = {
    "idle": "#808080",       # Gris
    "recording": "#FF0000",  # Rouge
    "processing": "#0080FF", # Bleu
    "error": "#FF4444",      # Rouge clair
}

# Cache de l'icone de base
_base_icon_cache: dict[int, Image.Image] = {}


def _hex_to_rgba(color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Convertit une couleur hex en tuple RGBA."""
    color = color.lstrip("#")
    if len(color) != 6:
        return (128, 128, 128, alpha)
    return (
        int(color[0:2], 16),
        int(color[2:4], 16),
        int(color[4:6], 16),
        alpha,
    )


def _sample_cubic_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int,
) -> list[tuple[float, float]]:
    """Echantillonne une courbe de Bezier cubique."""
    points: list[tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1.0 - t
        x = (
            (mt ** 3) * p0[0]
            + 3 * (mt ** 2) * t * p1[0]
            + 3 * mt * (t ** 2) * p2[0]
            + (t ** 3) * p3[0]
        )
        y = (
            (mt ** 3) * p0[1]
            + 3 * (mt ** 2) * t * p1[1]
            + 3 * mt * (t ** 2) * p2[1]
            + (t ** 3) * p3[1]
        )
        points.append((x, y))
    return points


def _draw_wave_logo(size: int) -> Image.Image:
    """Cree une icone vectorielle 'cercle + vagues' style orb."""
    if size in _base_icon_cache:
        return _base_icon_cache[size].copy()

    # Supersampling pour un rendu net aux petites tailles (16/24/32 px).
    scale = 4
    canvas_size = size * scale
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    cx = cy = canvas_size / 2
    radius = canvas_size * 0.45  # +10% visuel pour mieux matcher les icones app Windows
    ring_width = max(2, int(canvas_size * 0.03))

    # Halo subtil
    halo_radius = radius + canvas_size * 0.015
    draw.ellipse(
        [cx - halo_radius, cy - halo_radius, cx + halo_radius, cy + halo_radius],
        fill=(8, 16, 30, 70),
    )

    # Cercle principal
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=(18, 30, 52, 236),
        outline=(92, 120, 165, 190),
        width=ring_width,
    )

    # Tracé des vagues (reprend le path de orb.html, viewBox 100x100)
    start = (20.0, 45.0)
    curves = [
        ((22.0, 45.0), (26.0, 60.0), (32.0, 60.0)),
        ((38.0, 60.0), (38.0, 40.0), (42.0, 40.0)),
        ((46.0, 40.0), (46.0, 58.0), (50.0, 58.0)),
        ((54.0, 58.0), (54.0, 40.0), (58.0, 40.0)),
        ((62.0, 40.0), (62.0, 58.0), (66.0, 58.0)),
        ((70.0, 58.0), (74.0, 42.0), (80.0, 42.0)),
    ]

    wave_width = canvas_size * 0.54
    wave_scale = wave_width / 60.0  # path x: 20 -> 80

    def transform(pt: tuple[float, float]) -> tuple[float, float]:
        # Center path around (50,50), then scale and recenter in icon
        x = (pt[0] - 50.0) * wave_scale + cx
        y = (pt[1] - 50.0) * wave_scale + cy
        return (x, y)

    points: list[tuple[float, float]] = [transform(start)]
    prev = start
    for c1, c2, p3 in curves:
        sampled = _sample_cubic_bezier(prev, c1, c2, p3, steps=14)
        points.extend(transform(p) for p in sampled[1:])
        prev = p3

    wave_width_px = max(2, int(canvas_size * 0.045))
    draw.line(points, fill=(230, 236, 248, 240), width=wave_width_px, joint="curve")

    # Downsample final
    final_img = image.resize((size, size), Image.Resampling.LANCZOS)
    bbox = final_img.split()[-1].getbbox()
    if bbox:
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        logger.debug(f"icons idle bbox: size={size} bbox={bbox} content={bw}x{bh}")
    _base_icon_cache[size] = final_img
    return final_img.copy()


def create_icon(state: IconState = "idle", size: int = 64) -> Image.Image:
    """Cree une icone selon l'etat : cercle + vagues + badge colore.

    Args:
        state: Etat de l'application (idle, recording, processing, error).
        size: Taille de l'icone en pixels.

    Returns:
        Image PIL de l'icone.
    """
    image = _draw_wave_logo(size)

    # Ajouter un badge colore en bas a droite (sauf idle)
    if state != "idle":
        color = _hex_to_rgba(STATE_COLORS.get(state, STATE_COLORS["idle"]))
        draw = ImageDraw.Draw(image)
        badge_r = max(size // 8, 4)  # 8 px @64
        bx = size - badge_r - max(size // 40, 2)
        by = size - badge_r - max(size // 40, 2)
        # Fond blanc pour le contour du badge
        draw.ellipse(
            [bx - badge_r - 1, by - badge_r - 1, bx + badge_r + 1, by + badge_r + 1],
            fill=(255, 255, 255, 255),
        )
        # Badge colore
        draw.ellipse(
            [bx - badge_r, by - badge_r, bx + badge_r, by + badge_r],
            fill=color,
        )

    return image


def create_qicon(state: IconState = "idle", size: int = 64) -> QIcon:
    """Cree un QIcon PySide6 selon l'etat de l'application.

    Args:
        state: Etat de l'application.
        size: Taille de l'icone en pixels.

    Returns:
        QIcon PySide6.
    """
    pil_image = create_icon(state, size)
    # PIL RGBA -> QImage
    data = pil_image.tobytes("raw", "RGBA")
    qimage = QImage(data, size, size, 4 * size, QImage.Format_RGBA8888).copy()
    pixmap = QPixmap.fromImage(qimage)
    return QIcon(pixmap)


def force_taskbar_icon_win32(hwnd: int) -> None:
    """Force l'icone barre des taches Windows via WM_SETICON (Win32 API).

    Qt ne re-envoie pas toujours WM_SETICON quand la fenetre demarre minimisee.
    Cette fonction sauvegarde l'icone generee en .ico temporaire et l'applique
    directement pour garantir la coherence taskbar/tray.

    Args:
        hwnd: Handle Windows de la fenetre (int(widget.winId())).
    """
    import os
    import tempfile
    import ctypes

    icon_img = create_icon("idle", 256)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".ico", delete=False) as f:
            tmp_path = f.name
        print(f"[TaskbarIcon] Sauvegarde ICO dans : {tmp_path}", flush=True)
        icon_img.save(
            tmp_path,
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
        print(f"[TaskbarIcon] ICO sauvegarde OK ({os.path.getsize(tmp_path)} octets)", flush=True)

        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        LR_DEFAULTSIZE = 0x00000040

        hicon = ctypes.windll.user32.LoadImageW(
            None, tmp_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE
        )
        print(f"[TaskbarIcon] LoadImageW -> hicon = {hicon}", flush=True)
        if hicon:
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
            print(f"[TaskbarIcon] WM_SETICON envoye au HWND {hwnd} -> OK", flush=True)
            logger.debug("force_taskbar_icon_win32: icone appliquee")
        else:
            err = ctypes.GetLastError()
            print(f"[TaskbarIcon] ERREUR: LoadImageW a retourne 0 (GetLastError={err})", flush=True)
            logger.warning(f"force_taskbar_icon_win32: LoadImageW a echoue (err={err})")
    except Exception as e:
        logger.warning(f"force_taskbar_icon_win32: erreur: {e}")
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
