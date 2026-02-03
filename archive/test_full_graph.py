#!/usr/bin/env python3
"""Test script showing the full graph with all three curves using simulated data."""

import math
import json
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

def polynomial_fit_interpolate(t_min, events, degree=3):
    """Fit a polynomial and interpolate."""
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
    """Linear interpolation."""
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
    """Half-sine interpolation."""
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

# Create realistic test data
# Simulating Goat Rock tides for today
goat_rock_tides = [
    ("Low", "2:09 AM", "3.3ft"),
    ("High", "7:56 AM", "6.6ft"),
    ("Low", "3:29 PM", "-1.1ft"),
    ("High", "10:24 PM", "4.7ft"),
]

# Estuary tides (delayed from Bodega)
estuary_tides = [
    ("Low", "3:39 AM", "2.8ft"),
    ("High", "9:26 AM", "5.5ft"),
    ("Low", "5:29 PM", "-1.8ft"),
    ("High", "11:54 PM", "3.9ft"),
]

# Jenner stage measurements (hourly from 6am to 11pm)
jenner_stage_history = [
    {"time": "6:00 AM", "minutes": 360, "stage": 4.2},
    {"time": "7:00 AM", "minutes": 420, "stage": 4.8},
    {"time": "8:00 AM", "minutes": 480, "stage": 5.4},
    {"time": "9:00 AM", "minutes": 540, "stage": 5.9},
    {"time": "10:00 AM", "minutes": 600, "stage": 6.1},
    {"time": "11:00 AM", "minutes": 660, "stage": 5.8},
    {"time": "12:00 PM", "minutes": 720, "stage": 5.2},
    {"time": "1:00 PM", "minutes": 780, "stage": 4.5},
    {"time": "2:00 PM", "minutes": 840, "stage": 3.8},
    {"time": "3:00 PM", "minutes": 900, "stage": 3.1},
    {"time": "4:00 PM", "minutes": 960, "stage": 2.4},
    {"time": "5:00 PM", "minutes": 1020, "stage": 1.8},
    {"time": "6:00 PM", "minutes": 1080, "stage": 1.3},
    {"time": "7:00 PM", "minutes": 1140, "stage": 1.5},
    {"time": "8:00 PM", "minutes": 1200, "stage": 2.1},
    {"time": "9:00 PM", "minutes": 1260, "stage": 2.9},
    {"time": "10:00 PM", "minutes": 1320, "stage": 3.8},
    {"time": "11:00 PM", "minutes": 1380, "stage": 4.5},
]

def parse_tides(tides):
    events = []
    for label, time_str, height_str in tides:
        # Parse time
        if "AM" in time_str or "PM" in time_str:
            dt = datetime.strptime(time_str, "%I:%M %p")
        else:
            dt = datetime.strptime(time_str.strip("0"), "%H:%M")
        t_min = dt.hour * 60 + dt.minute
        h_val = float(height_str.replace("ft", "").strip())
        events.append((t_min, h_val))
    return sorted(events)

goat_rock_events = parse_tides(goat_rock_tides)
estuary_events = parse_tides(estuary_tides)
jenner_events = [(m["minutes"], m["stage"]) for m in jenner_stage_history]

print("Goat Rock tides:")
for t, h in goat_rock_events:
    print(f"  {int(t/60):2d}:{t%60:02d}: {h:.1f}ft")

print("\nEstuary tides:")
for t, h in estuary_events:
    print(f"  {int(t/60):2d}:{t%60:02d}: {h:.1f}ft")

print("\nJenner stage measurements:")
for t, h in jenner_events:
    print(f"  {int(t/60):2d}:{t%60:02d}: {h:.1f}ft")

# Create image (portrait mode)
width, height = 300, 120
img = Image.new("1", (width, height), 255)
draw = ImageDraw.Draw(img)

try:
    small_text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
except:
    small_text_font = ImageFont.load_default()

# Graph parameters (matching the main display)
margin_left = 12
margin_right = 3
margin_top = 3
margin_bottom = 12

graph_width = width - margin_left - margin_right
graph_height = height - margin_top - margin_bottom

# Scale: -2 to 8 ft
h_min, h_max = -2, 8
h_range = h_max - h_min

# Draw axis box
draw.rectangle(
    (margin_left, margin_top, width - margin_right, height - margin_bottom),
    outline=0, fill=255
)

# Sample every 15 minutes
step = 15
points_gr = []
points_est = []
points_jenner = []

for t_min in range(0, 24 * 60 + 1, step):
    h_gr = half_sine_interpolate(t_min, goat_rock_events)
    h_est = half_sine_interpolate(t_min, estuary_events)
    h_jen = polynomial_fit_interpolate(t_min, jenner_events, degree=3)
    
    if h_gr is not None:
        px = margin_left + int((t_min / 1440) * graph_width)
        py_gr = height - margin_bottom - int(((h_gr - h_min) / h_range) * graph_height)
        points_gr.append((px, py_gr))
    
    if h_est is not None:
        px = margin_left + int((t_min / 1440) * graph_width)
        py_est = height - margin_bottom - int(((h_est - h_min) / h_range) * graph_height)
        points_est.append((px, py_est))
    
    if h_jen is not None:
        px = margin_left + int((t_min / 1440) * graph_width)
        py_jen = height - margin_bottom - int(((h_jen - h_min) / h_range) * graph_height)
        points_jenner.append((px, py_jen))

# Draw Goat Rock curve (solid line)
if len(points_gr) > 1:
    for i in range(len(points_gr) - 1):
        draw.line((points_gr[i], points_gr[i + 1]), fill=0, width=1)

# Draw Estuary curve (dashed line - every other point)
if len(points_est) > 1:
    for i in range(0, len(points_est) - 1, 2):
        draw.line((points_est[i], points_est[i + 1]), fill=0, width=1)

# Draw Jenner Stage curve (dotted line - every third point)
if len(points_jenner) > 1:
    print(f"\nJenner curve has {len(points_jenner)} points")
    print("Drawing dotted line (every 3rd point):")
    for i in range(0, len(points_jenner) - 1, 3):
        print(f"  Point {i} to {i+1}: ({points_jenner[i][0]}, {points_jenner[i][1]}) -> ({points_jenner[i+1][0]}, {points_jenner[i+1][1]})")
        draw.line((points_jenner[i], points_jenner[i + 1]), fill=0, width=1)

# Draw y-axis labels and markers
for h_label in [-2, 0, 2, 4, 6, 8]:
    py = height - margin_bottom - int(((h_label - h_min) / h_range) * graph_height)
    draw.line((margin_left - 2, py, margin_left, py), fill=0, width=1)
    label_text = str(h_label)
    label_bbox = draw.textbbox((0, 0), label_text, font=small_text_font)
    label_width = label_bbox[2] - label_bbox[0]
    draw.text((margin_left - 4 - label_width, py - 2), label_text, font=small_text_font, fill=0)

# Draw x-axis labels
for h_label in [4, 8, 12, 16, 20]:
    t_min = h_label * 60
    px = margin_left + int((t_min / 1440) * graph_width)
    py = height - margin_bottom + 1
    draw.line((px, height - margin_bottom, px, height - margin_bottom + 2), fill=0, width=1)
    label = f"{h_label}:00"
    draw.text((px - 8, py), label, font=small_text_font, fill=0)

# Save image
img.save("d:/GitHub/tides/full_graph_test.png")
print(f"\nSaved full graph to: d:/GitHub/tides/full_graph_test.png")
print(f"Image size: {width}x{height} pixels")
print(f"Graph area: {graph_width}x{graph_height} pixels")
