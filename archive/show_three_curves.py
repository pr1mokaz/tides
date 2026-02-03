#!/usr/bin/env python3
"""Create a clear, zoomed visualization showing just the graph with three curves."""

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

# Get tides
goat_rock = data.get("goat_rock", {}).get(today, [])
estuary = data.get("estuary", {}).get(today, [])
jenner_stage = data.get("jenner_stage_history", {}).get(today, [])

# Parse tide times
def parse_time(t_str):
    if "AM" in t_str or "PM" in t_str:
        dt = datetime.strptime(t_str, "%I:%M %p")
    else:
        dt = datetime.strptime(t_str.strip("0"), "%H:%M")
    return dt.hour * 60 + dt.minute

goat_events = [(parse_time(t), float(h.replace("ft", "").strip())) for _, t, h in goat_rock]
estuary_events = [(parse_time(t), float(h.replace("ft", "").strip())) for _, t, h in estuary]
jenner_events = [(m["minutes"], m["stage"]) for m in jenner_stage]

print(f"Goat Rock: {len(goat_events)} points")
print(f"Estuary: {len(estuary_events)} points")
print(f"Jenner: {len(jenner_events)} points")

# Create larger, clearer image
width, height = 800, 400
img = Image.new("1", (width, height), 255)
draw = ImageDraw.Draw(img)

try:
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
except:
    title_font = label_font = ImageFont.load_default()

# Title
draw.text((20, 10), "JENNER US1 BRIDGE - THREE CURVES VISUALIZATION", font=title_font, fill=0)

# Graph area
margin_left = 60
margin_right = 30
margin_top = 50
margin_bottom = 50

graph_width = width - margin_left - margin_right
graph_height = height - margin_top - margin_bottom

h_min, h_max = -2, 8
h_range = h_max - h_min

# Draw axis box
draw.rectangle((margin_left, margin_top, width - margin_right, height - margin_bottom), outline=0, fill=255)

# Sample curves
step = 10
points_gr = []
points_est = []
points_jen = []

for t_min in range(0, 1441, step):
    h_gr = half_sine_interpolate(t_min, goat_events)
    h_est = half_sine_interpolate(t_min, estuary_events)
    h_jen = polynomial_fit_interpolate(t_min, jenner_events, degree=3)
    
    if h_gr:
        px = margin_left + int((t_min / 1440) * graph_width)
        py = height - margin_bottom - int(((h_gr - h_min) / h_range) * graph_height)
        points_gr.append((px, py))
    if h_est:
        px = margin_left + int((t_min / 1440) * graph_width)
        py = height - margin_bottom - int(((h_est - h_min) / h_range) * graph_height)
        points_est.append((px, py))
    if h_jen:
        px = margin_left + int((t_min / 1440) * graph_width)
        py = height - margin_bottom - int(((h_jen - h_min) / h_range) * graph_height)
        points_jen.append((px, py))

print(f"\nInterpolated points:")
print(f"  Goat Rock: {len(points_gr)} points")
print(f"  Estuary: {len(points_est)} points")
print(f"  Jenner: {len(points_jen)} points")

# Draw Goat Rock (solid line, width=2)
if len(points_gr) > 1:
    for i in range(len(points_gr) - 1):
        draw.line((points_gr[i], points_gr[i + 1]), fill=0, width=2)
    print("  Drew Goat Rock solid line")

# Draw Estuary (dashed line - every 2nd point, width=2)
if len(points_est) > 1:
    for i in range(0, len(points_est) - 1, 2):
        draw.line((points_est[i], points_est[i + 1]), fill=0, width=2)
    print("  Drew Estuary dashed line")

# Draw Jenner (dotted line - every 3rd point, width=3 for visibility)
if len(points_jen) > 1:
    for i in range(0, len(points_jen) - 1, 3):
        draw.line((points_jen[i], points_jen[i + 1]), fill=0, width=3)
    print("  Drew Jenner dotted line")

# Draw y-axis
for h_label in [-2, 0, 2, 4, 6, 8]:
    py = height - margin_bottom - int(((h_label - h_min) / h_range) * graph_height)
    draw.line((margin_left - 5, py, margin_left, py), fill=0, width=1)
    label_text = f"{h_label:d}ft"
    draw.text((margin_left - 50, py - 6), label_text, font=label_font, fill=0)

# Draw x-axis
for h_label in [0, 4, 8, 12, 16, 20, 24]:
    t_min = h_label * 60
    px = margin_left + int((t_min / 1440) * graph_width)
    draw.line((px, height - margin_bottom, px, height - margin_bottom + 5), fill=0, width=1)
    label = f"{h_label:2d}:00"
    draw.text((px - 20, height - margin_bottom + 10), label, font=label_font, fill=0)

# Legend with visual examples
legend_y = height - 25
draw.line([(20, legend_y), (50, legend_y)], fill=0, width=2)
draw.text((60, legend_y - 6), "Goat Rock (Solid)", font=label_font, fill=0)

draw.line([(250, legend_y), (265, legend_y)], fill=0, width=2)
draw.line([(280, legend_y), (295, legend_y)], fill=0, width=2)
draw.text((310, legend_y - 6), "Estuary (Dashed)", font=label_font, fill=0)

draw.line([(520, legend_y), (530, legend_y)], fill=0, width=3)
draw.line([(540, legend_y), (550, legend_y)], fill=0, width=3)
draw.text((560, legend_y - 6), "Jenner Stage (Dotted)", font=label_font, fill=0)

# Save
img.save("d:/GitHub/tides/THREE_CURVES_VISUALIZATION.png")
print(f"\nSaved high-quality visualization to: THREE_CURVES_VISUALIZATION.png")
