#!/usr/bin/env python3
"""Simple test program for Pimoroni Inky Impression 4" 7-colour HAT (PIM600)."""
import sys
import os
from PIL import Image, ImageDraw, ImageFont

INKY_AVAILABLE = False
if os.environ.get("TIDES_EPAPER", "1") != "0" and sys.platform.startswith("linux"):
    try:
        from inky.auto import auto
        INKY_AVAILABLE = True
    except Exception:
        try:
            from inky import InkyImpression
            INKY_AVAILABLE = True
        except Exception:
            try:
                from inky.impression import InkyImpression
                INKY_AVAILABLE = True
            except Exception:
                try:
                    from inky.inky import InkyImpression
                    INKY_AVAILABLE = True
                except Exception:
                    print("⚠ Inky library not available, will save PNG only")
                    INKY_AVAILABLE = False

WIDTH = 640
HEIGHT = 400

COLORS = [
    (0, 0, 0),        # Black
    (255, 255, 255),  # White
    (0, 0, 255),      # Blue
    (0, 255, 0),      # Green
    (255, 0, 0),      # Red
    (255, 255, 0),    # Yellow
    (255, 128, 0),    # Orange
]

LABELS = ["BLACK", "WHITE", "BLUE", "GREEN", "RED", "YELLOW", "ORANGE"]


def load_font():
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except Exception:
        return ImageFont.load_default()


def render_test_image(width, height):
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = load_font()

    # Title
    title = "PIM600 TEST PATTERN"
    bbox = draw.textbbox((0, 0), title, font=font)
    draw.text(((width - (bbox[2] - bbox[0])) // 2, 8), title, font=font, fill=(0, 0, 0))

    # Color bars
    bar_top = 40
    bar_height = 40
    for i, (color, label) in enumerate(zip(COLORS, LABELS)):
        y1 = bar_top + i * bar_height
        y2 = y1 + bar_height - 2
        draw.rectangle((10, y1, width - 10, y2), fill=color, outline=(0, 0, 0))
        draw.text((20, y1 + 10), label, font=font, fill=(0, 0, 0))

    # Border
    draw.rectangle((5, 5, width - 5, height - 5), outline=(0, 0, 0))
    return img


def main():
    inky = None
    global WIDTH, HEIGHT
    if INKY_AVAILABLE:
        try:
            try:
                from inky.auto import auto
                inky = auto()
            except Exception:
                try:
                    from inky import InkyImpression
                except Exception:
                    try:
                        from inky.impression import InkyImpression
                    except Exception:
                        from inky.inky import InkyImpression
                inky = InkyImpression()
            WIDTH, HEIGHT = inky.width, inky.height
        except Exception as e:
            print(f"⚠ Failed to init Inky Impression: {e}")
            inky = None

    img = render_test_image(WIDTH, HEIGHT)

    # Save PNG for verification
    out_path = os.path.join(os.path.dirname(__file__), "display_outputs", "pim600_test.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path)
    print(f"Saved test image to {out_path}")

    if inky:
        inky.set_image(img)
        inky.show()
        print("Display updated.")


if __name__ == "__main__":
    main()
