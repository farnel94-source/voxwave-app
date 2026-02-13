"""Generation d'icones dynamiques pour le system tray."""

import logging
from typing import Literal

from PIL import Image, ImageDraw
from PySide6.QtGui import QIcon, QImage, QPixmap

logger = logging.getLogger(__name__)

IconState = Literal["idle", "recording", "processing", "error"]

# Couleurs par etat
STATE_COLORS: dict[str, str] = {
    "idle": "#808080",       # Gris
    "recording": "#FF0000",  # Rouge
    "processing": "#0080FF", # Bleu
    "error": "#FF4444",      # Rouge clair
}


def create_icon(state: IconState = "idle", size: int = 64) -> Image.Image:
    """Cree une icone PIL selon l'etat de l'application.

    Args:
        state: Etat de l'application (idle, recording, processing, error).
        size: Taille de l'icone en pixels.

    Returns:
        Image PIL de l'icone.
    """
    color = STATE_COLORS.get(state, STATE_COLORS["idle"])
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Cercle principal
    margin = size // 8
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=color,
        outline="#FFFFFF",
        width=max(1, size // 16),
    )

    # Indicateur central selon l'etat
    center = size // 2
    if state == "recording":
        # Point blanc au centre (indicateur REC)
        r = size // 8
        draw.ellipse(
            [center - r, center - r, center + r, center + r],
            fill="#FFFFFF",
        )
    elif state == "processing":
        # Trois points (indicateur traitement)
        r = size // 16
        for offset in [-size // 6, 0, size // 6]:
            draw.ellipse(
                [center + offset - r, center - r, center + offset + r, center + r],
                fill="#FFFFFF",
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
    qimage = QImage(data, size, size, 4 * size, QImage.Format_RGBA8888)
    pixmap = QPixmap.fromImage(qimage)
    return QIcon(pixmap)
