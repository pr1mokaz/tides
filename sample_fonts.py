#!/usr/bin/env python3
"""Generate a sample image comparing DejaVu Sans and DejaVu Sans Condensed."""
import os
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 800, 600
BG = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)

SAMPLE_TEXTS = [
    "WEST RUSSIAN RIVER CONDITIONS",
    "COASTAL TIDES",
    "TIDE CURVES",
    "Hacienda Bridge Guernville: 7.21 ft 1234cfs",
    "US-1 Bridge Jenner: 6.78 ft",
    "Goat Rock: 08:32 5.1ft",
]

FONTS = {
    "DejaVu Sans": {
        "header": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "text": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    },
    "DejaVu Sans Condensed": {
        "header": "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        "text": "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
    },
}


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def main():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    x_left = 40
    x_right = 420
    y = 30

    for col, (name, paths) in enumerate(FONTS.items()):
        x = x_left if col == 0 else x_right
        draw.text((x, y), name, font=load_font(paths["header"], 22), fill=BLUE)
        y_offset = y + 40
        header_font = load_font(paths["header"], 20)
        text_font = load_font(paths["text"], 15)

        for i, line in enumerate(SAMPLE_TEXTS):
            font = header_font if i < 3 else text_font
            draw.text((x, y_offset), line, font=font, fill=BLACK)
            y_offset += 28

    out_path = os.path.join(os.path.dirname(__file__), "display_outputs", "font_comparison.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path)
    print(f"Saved sample image to {out_path}")


if __name__ == "__main__":
    main()
