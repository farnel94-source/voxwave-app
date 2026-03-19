"""Add rounded corners and drop shadow to screenshot images."""

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    print("Pillow required: pip install Pillow")
    sys.exit(1)


def add_rounded_corners_and_shadow(
    input_path: str,
    output_path: str | None = None,
    radius: int = 16,
    shadow_offset: int = 8,
    shadow_blur: int = 20,
    shadow_color: tuple = (0, 0, 0, 80),
    padding: int = 40,
) -> None:
    """Polish a screenshot with rounded corners and a drop shadow."""
    img = Image.open(input_path).convert("RGBA")
    w, h = img.size

    # Round corners mask
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), (w - 1, h - 1)], radius=radius, fill=255)
    img.putalpha(mask)

    # Shadow layer
    canvas_w = w + padding * 2
    canvas_h = h + padding * 2
    shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    shadow_rect = Image.new("RGBA", (w, h), shadow_color)
    shadow_rect.putalpha(mask)
    shadow.paste(
        shadow_rect,
        (padding + shadow_offset, padding + shadow_offset),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))

    # Composite image on top of shadow
    shadow.paste(img, (padding, padding), img)

    out = output_path or input_path
    shadow.save(out)
    print(f"Polished: {out} ({canvas_w}x{canvas_h})")


if __name__ == "__main__":
    assets = Path(__file__).resolve().parent.parent / "assets"

    targets = sys.argv[1:] if len(sys.argv) > 1 else ["settings.png"]

    for name in targets:
        path = assets / name
        if path.exists():
            add_rounded_corners_and_shadow(str(path))
        else:
            print(f"Skipped (not found): {path}")
