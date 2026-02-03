#!/usr/bin/env python3
"""Render a stage-only plot from jenner_stage_history without numpy."""

import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

DATA_FILE = "tides.json"
OUTPUT_FILE = "stage_only_plot.png"

WIDTH, HEIGHT = 600, 250
MARGIN = 30
H_MIN, H_MAX = -2, 10


def linear_interpolate(t_min, events):
    if not events or len(events) < 2:
        return None
    if t_min < events[0][0]:
        return None
    if t_min > events[-1][0]:
        return None
    for i in range(len(events) - 1):
        t1, v1 = events[i]
        t2, v2 = events[i + 1]
        if t1 <= t_min <= t2:
            if t2 == t1:
                return v1
            frac = (t_min - t1) / (t2 - t1)
            return v1 + frac * (v2 - v1)
    return None


def main():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    today = datetime(2026, 2, 2).strftime("%Y-%m-%d")
    stage_list = data.get("jenner_stage_history", {}).get(today, [])
    events = sorted(
        [(m["minutes"], float(m["stage"])) for m in stage_list if m.get("minutes") is not None and m.get("stage") is not None]
    )

    if len(events) < 2:
        print("Not enough data to plot")
        return

    img = Image.new("1", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except Exception:
        font = ImageFont.load_default()

    # Axes
    draw.rectangle((MARGIN, MARGIN, WIDTH - MARGIN, HEIGHT - MARGIN), outline=0, fill=255)

    # Plot line
    pts = []
    for t_min in range(0, 1441, 10):
        h = linear_interpolate(t_min, events)
        if h is None:
            continue
        x = MARGIN + int((t_min / 1440) * (WIDTH - 2 * MARGIN))
        y = HEIGHT - MARGIN - int(((h - H_MIN) / (H_MAX - H_MIN)) * (HEIGHT - 2 * MARGIN))
        pts.append((x, y))

    for i in range(len(pts) - 1):
        draw.line((pts[i], pts[i + 1]), fill=0, width=2)

    # Plot points
    for t_min, h in events:
        x = MARGIN + int((t_min / 1440) * (WIDTH - 2 * MARGIN))
        y = HEIGHT - MARGIN - int(((h - H_MIN) / (H_MAX - H_MIN)) * (HEIGHT - 2 * MARGIN))
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=0)

    draw.text((MARGIN, 5), f"Stage-only plot (linear interp) {today}", font=font, fill=0)
    img.save(OUTPUT_FILE)
    print(f"Saved {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
