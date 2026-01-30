#!/usr/bin/env python3
"""Test script to render portrait display without waveshare library."""
import json
import math
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

WIDTH = 300
HEIGHT = 400

def load_fonts():
    try:
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        section_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        header_font = section_font = text_font = ImageFont.load_default()
    return header_font, section_font, text_font

def time_str_to_minutes(time_str):
    """Convert '2:30 PM' to minutes since midnight."""
    try:
        if "AM" in time_str or "PM" in time_str:
            dt = datetime.strptime(time_str, "%I:%M %p")
        else:
            dt = datetime.strptime(time_str.lstrip("0"), "%H:%M")
        return dt.hour * 60 + dt.minute
    except:
        return None

def half_sine_interpolate(t_min, events):
    """Interpolate tide height using half-sine between events."""
    if not events or len(events) < 2:
        return None
    if t_min < events[0][0]:
        return events[0][1]
    if t_min > events[-1][0]:
        return events[-1][1]
    
    for i in range(len(events) - 1):
        t1, h1 = events[i]
        t2, h2 = events[i + 1]
        if t1 <= t_min <= t2:
            if t2 == t1:
                return h1
            m = 0.5 * (h1 + h2)
            a = 0.5 * (h2 - h1)
            frac = (t_min - t1) / (t2 - t1)
            theta = math.pi * frac - math.pi / 2
            return m + a * math.sin(theta)
    return None

def draw_tide_waveform(draw, x, y, width, height, tides, text_font):
    """Draw tide waveform."""
    # Parse tides
    events = []
    for label, time_str, height_str in tides:
        t_min = time_str_to_minutes(time_str)
        h_val = float(height_str.replace("ft", "").strip())
        if t_min is not None:
            events.append((t_min, h_val))
    
    if not events or len(events) < 2:
        draw.text((x, y), "No tide data", font=text_font, fill=0)
        return
    
    events.sort()
    heights = [h for _, h in events]
    h_min, h_max = min(heights), max(heights)
    h_range = h_max - h_min
    if h_range < 0.1:
        h_range = 1.0
    
    margin_left, margin_right = 3, 3
    margin_top, margin_bottom = 3, 10
    graph_width = width - margin_left - margin_right
    graph_height = height - margin_top - margin_bottom
    
    # Sample every 30 minutes
    points = []
    for t_min in range(0, 24 * 60, 30):
        h = half_sine_interpolate(t_min, events)
        if h is not None:
            px = x + margin_left + int((t_min / 1440) * graph_width)
            py = y + height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
            points.append((px, py))
    
    # Draw axis box
    draw.rectangle((x + margin_left, y + margin_top, x + width - margin_right, y + height - margin_bottom), outline=0)
    
    # Draw waveform
    if len(points) > 1:
        for i in range(len(points) - 1):
            draw.line((points[i], points[i + 1]), fill=0, width=1)
    
    # Time labels
    for label, t_min in [("00:00", 0), ("12:00", 12*60), ("24:00", 24*60)]:
        px = x + margin_left + int((t_min / 1440) * graph_width)
        py = y + height - margin_bottom + 1
        draw.text((px - 8, py), label, font=text_font, fill=0)

# Load data and render
with open('tides.json') as f:
    data = json.load(f)

from datetime import date as dateobj
today_key = dateobj.today().strftime("%Y-%m-%d")
goat_rock_tides = data.get("goat_rock", {}).get(today_key, [])

img = Image.new("1", (WIDTH, HEIGHT), 255)
draw = ImageDraw.Draw(img)
header_font, section_font, text_font = load_fonts()

# Simple layout
draw.rectangle((0, 0, WIDTH, 28), fill=0)
date_str = dateobj.today().strftime("%b %d, %Y")
bbox = draw.textbbox((0, 0), f"TIDES - {date_str}", font=header_font)
draw.text(((WIDTH-(bbox[2]-bbox[0]))//2, 4), f"TIDES - {date_str}", font=header_font, fill=255)

# Goat Rock info
draw.text((10, 40), "GOAT ROCK PREDICTIONS", font=section_font, fill=0)
y = 60
for label, t, h in goat_rock_tides[:4]:
    draw.text((10, y), f"{label}: {t} {h}", font=text_font, fill=0)
    y += 14

# Waveform
draw.text((10, 130), "TIDE CURVE", font=section_font, fill=0)
draw_tide_waveform(draw, 10, 145, WIDTH-20, 100, goat_rock_tides, text_font)

img.save('test_portrait.png')
print('Saved test_portrait.png')
