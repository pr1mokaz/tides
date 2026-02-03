#!/usr/bin/env python3
"""Test to show the improved day boundary handling for the Jenner stage curve."""

import math
import json
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

def polynomial_fit_interpolate(t_min, events, degree=3):
    if not events or len(events) < 2:
        return None
    if t_min < events[0][0]:
        return events[0][1]
    if t_min > events[-1][0]:
        return events[-1][1]
    
    try:
        import numpy as np
        times = np.array([e[0] for e in events])
        values = np.array([e[1] for e in events])
        actual_degree = min(degree, len(events) - 1)
        coeffs = np.polyfit(times, values, actual_degree)
        poly = np.poly1d(coeffs)
        return float(poly(t_min))
    except:
        return linear_interpolate(t_min, events)

def linear_interpolate(t_min, events):
    if not events or len(events) < 1:
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
            frac = (t_min - t1) / (t2 - t1)
            return h1 + frac * (h2 - h1)
    return None

def half_sine_interpolate(t_min, events):
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

# Load data
with open('d:/GitHub/tides/tides.json', 'r') as f:
    data = json.load(f)

today = "2026-02-02"
yesterday = "2026-02-01"

# Get measurements for both days
yesterday_jenner = data.get("jenner_stage_history", {}).get(yesterday, [])
today_jenner = data.get("jenner_stage_history", {}).get(today, [])

print(f"Yesterday ({yesterday}): {len(yesterday_jenner)} measurements")
for m in yesterday_jenner[-2:]:  # Show last 2
    print(f"  {m['time']:12} ({m['minutes']:4}min): {m['stage']:.1f}ft")

print(f"\nToday ({today}): {len(today_jenner)} measurements")
for m in today_jenner[:3]:  # Show first 3
    print(f"  {m['time']:12} ({m['minutes']:4}min): {m['stage']:.1f}ft")

# Parse and combine both days
def parse_stage(stage_list, offset):
    return [(m["minutes"] + offset, m["stage"]) for m in stage_list]

# Create combined event list with day boundary
yesterday_events = parse_stage(yesterday_jenner, -1440)  # Prior day offset by -24*60
today_events = parse_stage(today_jenner, 0)             # Today starts at 0
combined_events = sorted(yesterday_events + today_events)

print(f"\nCombined events across day boundary: {len(combined_events)} points")
print(f"First point: {combined_events[0][0]:5} min = {combined_events[0][1]:.1f}ft (yesterday 8:00 PM)")
print(f"Midnight: -960 min should have a value")
print(f"Last point: {combined_events[-1][0]:5} min = {combined_events[-1][1]:.1f}ft (today 11:00 PM)")

# Create visualization
img_width, img_height = 900, 350
img = Image.new("1", (img_width, img_height), 255)
draw = ImageDraw.Draw(img)

try:
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except:
    title_font = label_font = ImageFont.load_default()

# Title
draw.text((20, 10), "DAY BOUNDARY HANDLING - Continuous Curve from Yesterday into Today", font=title_font, fill=0)

# Graph
margin_left = 60
margin_right = 30
margin_top = 40
margin_bottom = 60

graph_width = img_width - margin_left - margin_right
graph_height = img_height - margin_top - margin_bottom

h_min, h_max = -2, 8
h_range = h_max - h_min

# Draw axis
draw.rectangle((margin_left, margin_top, img_width - margin_right, img_height - margin_bottom), outline=0, fill=255)

# Draw curve
step = 15
points = []
for t_min in range(-1440, 1441, step):
    h = polynomial_fit_interpolate(t_min, combined_events, degree=3)
    if h is not None:
        px = margin_left + int(((t_min + 1440) / 2880) * graph_width)  # Map -1440 to 1440 onto graph width
        py = img_height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
        points.append((px, py))

if len(points) > 1:
    for i in range(len(points) - 1):
        draw.line([(points[i][0], points[i][1]), (points[i + 1][0], points[i + 1][1])], fill=0, width=2)
    print(f"\nDrew curve with {len(points)} interpolated points")

# Draw measurement points
for t_min, h in combined_events:
    px = margin_left + int(((t_min + 1440) / 2880) * graph_width)
    py = img_height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
    r = 2
    draw.ellipse((px-r, py-r, px+r, py+r), fill=0)

# Mark midnight boundary
midnight_x = margin_left + int((1440 / 2880) * graph_width)  # 1440 minutes into the 2880 range
draw.line([(midnight_x, margin_top), (midnight_x, img_height - margin_bottom)], fill=0, width=1)
draw.text((midnight_x - 15, img_height - margin_bottom + 10), "Midnight", font=label_font, fill=0)

# Y-axis
for h_label in [0, 2, 4, 6, 8]:
    py = img_height - margin_bottom - int(((h_label - h_min) / h_range) * graph_height)
    draw.line([(margin_left - 3, py), (margin_left, py)], fill=0, width=1)
    draw.text((margin_left - 30, py - 5), f"{h_label}ft", font=label_font, fill=0)

# X-axis labels
labels = [
    (-1440, "-24h (Yest."),
    (-1200, "-20h"),
    (-900, "-15h"),
    (-600, "-10h"),
    (-300, "-5h"),
    (0, "TODAY"),
    (300, "+5h"),
    (600, "+10h"),
    (900, "+15h"),
    (1200, "+20h"),
    (1440, "+24h"),
]

for t_min, label in labels:
    px = margin_left + int(((t_min + 1440) / 2880) * graph_width)
    draw.line([(px, img_height - margin_bottom), (px, img_height - margin_bottom + 3)], fill=0, width=1)
    draw.text((px - 15, img_height - margin_bottom + 5), label, font=label_font, fill=0)

# Legend
draw.text((20, img_height - 30), "Early morning (0:00-6:00) now shows continuous curve from yesterday - NO MORE FLAT LINES", font=label_font, fill=0)

img.save("d:/GitHub/tides/BOUNDARY_HANDLING_TEST.png")
print(f"\nSaved visualization to: BOUNDARY_HANDLING_TEST.png")
