"""Generation d'icones dynamiques pour le system tray."""

import logging
import os
from typing import Literal

from PIL import Image, ImageDraw
from PySide6.QtGui import QIcon, QImage, QPixmap

from src.utils.platform import resource_path

logger = logging.getLogger(__name__)

IconState = Literal["idle", "recording", "processing", "error"]

# Couleurs par etat (pour le badge indicateur)
STATE_COLORS: dict[str, str] = {
    "idle": "#808080",       # Gris
    "recording": "#FF0000",  # Rouge
    "processing": "#0080FF", # Bleu
    "error": "#FF4444",      # Rouge clair
}

# Cache du logo redimensionne
_logo_cache: dict[int, Image.Image] = {}


def _load_logo(size: int) -> Image.Image:
    """Charge et redimensionne le logo The Wave.

    Args:
        size: Taille cible en pixels.

    Returns:
        Image PIL RGBA du logo redimensionne.
    """
    if size in _logo_cache:
        return _logo_cache[size].copy()

    logo_path = resource_path(os.path.join("src", "gui", "orb", "logo.png"))
    try:
        logo = Image.open(logo_path).convert("RGBA")
        logo = logo.resize((size, size), Image.Resampling.LANCZOS)
        _logo_cache[size] = logo
        return logo.copy()
    except Exception as e:
        logger.warning(f"Logo introuvable ({logo_path}), fallback cercle: {e}")
        return None


def create_icon(state: IconState = "idle", size: int = 64) -> Image.Image:
    """Cree une icone selon l'etat : logo The Wave + badge colore.

    Args:
        state: Etat de l'application (idle, recording, processing, error).
        size: Taille de l'icone en pixels.

    Returns:
        Image PIL de l'icone.
    """
    # Essayer de charger le logo
    logo = _load_logo(size)
    if logo is not None:
        image = logo
    else:
        # Fallback: cercle colore (ancien comportement)
        color = STATE_COLORS.get(state, STATE_COLORS["idle"])
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        margin = size // 8
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=color, outline="#FFFFFF", width=max(1, size // 16),
        )
        return image

    # Ajouter un badge colore en bas a droite (sauf idle)
    if state != "idle":
        color = STATE_COLORS.get(state, STATE_COLORS["idle"])
        draw = ImageDraw.Draw(image)
        badge_r = max(size // 8, 4)
        bx = size - badge_r - 1
        by = size - badge_r - 1
        # Fond blanc pour le contour du badge
        draw.ellipse(
            [bx - badge_r - 1, by - badge_r - 1, bx + badge_r + 1, by + badge_r + 1],
            fill="#FFFFFF",
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
    Cette fonction sauvegarde le logo en .ico temporaire et l'applique directement.

    Args:
        hwnd: Handle Windows de la fenetre (int(widget.winId())).
    """
    import os
    import tempfile
    import ctypes

    logo = _load_logo(256)
    if logo is None:
        logger.warning("force_taskbar_icon_win32: logo introuvable, abandon")
        return

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".ico", delete=False) as f:
            tmp_path = f.name
        print(f"[TaskbarIcon] Sauvegarde ICO dans : {tmp_path}", flush=True)
        logo.save(tmp_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
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
