"""Génération d'icônes dynamiques pour le system tray."""

import logging
from typing import Literal

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

IconState = Literal["idle", "recording", "processing", "error"]

# Couleurs par état
STATE_COLORS: dict[str, str] = {
    "idle": "#808080",       # Gris
    "recording": "#FF0000",  # Rouge
    "processing": "#0080FF", # Bleu
    "error": "#FF4444",      # Rouge clair
}


def create_icon(state: IconState = "idle", size: int = 64) -> Image.Image:
    """Crée une icône PIL selon l'état de l'application.

    Args:
        state: État de l'application (idle, recording, processing, error).
        size: Taille de l'icône en pixels.

    Returns:
        Image PIL de l'icône.
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

    # Indicateur central selon l'état
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
