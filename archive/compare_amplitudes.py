#!/usr/bin/env python3
"""Compare tides vs stage to show they have similar amplitude but different offsets."""

import math
import json
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

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
        return None

def parse_time(t_str):
    if "AM" in t_str or "PM" in t_str:
        dt = datetime.strptime(t_str, "%I:%M %p")
    else:
        dt = datetime.strptime(t_str.strip("0"), "%H:%M")
    return dt.hour * 60 + dt.minute

with open('d:/GitHub/tides/tides.json', 'r') as f:
    data = json.load(f)

today = "2026-02-02"
yesterday = "2026-02-01"

# Get tides
goat_rock_today = data.get("goat_rock", {}).get(today, [])
goat_rock_yesterday = data.get("goat_rock", {}).get(yesterday, [])

# Get stage
stage_today = data.get("jenner_stage_history", {}).get(today, [])
stage_yesterday = data.get("jenner_stage_history", {}).get(yesterday, [])

# Parse
def parse_tides(tides, offset=0):
    return [(parse_time(t) + offset, float(h.replace("ft", "").strip())) for _, t, h in tides]

def parse_stage(stage_list, offset=0):
    return [(m["minutes"] + offset, m["stage"]) for m in stage_list]

tide_events = sorted(parse_tides(goat_rock_yesterday, -1440) + parse_tides(goat_rock_today, 0))
stage_events = sorted(parse_stage(stage_yesterday, -1440) + parse_stage(stage_today, 0))

# Calculate stats
tide_values = [h for _, h in tide_events]
stage_values = [h for _, h in stage_events if 0 <= _ <= 1440]  # Today only

print(f"Tide statistics (full range):")
print(f"  Range: {min(tide_values):.1f} to {max(tide_values):.1f} ft")
print(f"  Peak-to-peak: {max(tide_values) - min(tide_values):.1f} ft")
print(f"  Mean: {sum(tide_values)/len(tide_values):.1f} ft")

print(f"\nStage statistics (today 0:00-24:00):")
print(f"  Range: {min(stage_values):.1f} to {max(stage_values):.1f} ft")
print(f"  Peak-to-peak: {max(stage_values) - min(stage_values):.1f} ft")
print(f"  Mean: {sum(stage_values)/len(stage_values):.1f} ft")

# Create visualization
img_width, img_height = 1000, 400
img = Image.new("1", (img_width, img_height), 255)
draw = ImageDraw.Draw(img)

try:
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except:
    title_font = label_font = ImageFont.load_default()

draw.text((20, 10), "AMPLITUDE COMPARISON: Tidal Predictions vs Water Stage Measurements", font=title_font, fill=0)

# Draw two graphs side by side
def draw_curve_graph(draw, x_offset, y_offset, width, height, events, title, color_points=False):
    margin_left = 50
    margin_right = 20
    margin_top = 35
    margin_bottom = 50
    
    graph_width = width - margin_left - margin_right
    graph_height = height - margin_top - margin_bottom
    
    h_min, h_max = -2, 8
    h_range = h_max - h_min
    
    # Background
    draw.rectangle((x_offset, y_offset, x_offset + width, y_offset + height), outline=0, fill=255)
    draw.rectangle((x_offset + margin_left, y_offset + margin_top, x_offset + width - margin_right, 
                   y_offset + height - margin_bottom), outline=0, fill=255)
    
    # Title
    draw.text((x_offset + 10, y_offset + 5), title, font=label_font, fill=0)
    
    # Draw curve for today only (0 to 1440 minutes)
    points = []
    for t_min in range(0, 1441, 15):
        if events:
            h = half_sine_interpolate(t_min, events) if "tide" in title.lower() else polynomial_fit_interpolate(t_min, events)
            if h is not None:
                px = x_offset + margin_left + int((t_min / 1440) * graph_width)
                py = y_offset + height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
                points.append((px, py))
    
    # Draw curve
    if len(points) > 1:
        for i in range(len(points) - 1):
            draw.line([(points[i][0], points[i][1]), (points[i + 1][0], points[i + 1][1])], fill=0, width=2)
    
    # Draw measurement points
    for t_min, h in events:
        if 0 <= t_min <= 1440:
            px = x_offset + margin_left + int((t_min / 1440) * graph_width)
            py = y_offset + height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
            r = 2
            draw.ellipse((px-r, py-r, px+r, py+r), fill=0)
    
    # Y-axis
    for h_label in [-2, 0, 2, 4, 6, 8]:
        py = y_offset + height - margin_bottom - int(((h_label - h_min) / h_range) * graph_height)
        draw.line([(x_offset + margin_left - 3, py), (x_offset + margin_left, py)], fill=0, width=1)
        draw.text((x_offset + 15, py - 4), f"{h_label}ft", font=label_font, fill=0)
    
    # X-axis
    for hour in [0, 6, 12, 18, 24]:
        t_min = hour * 60
        px = x_offset + margin_left + int((t_min / 1440) * graph_width)
        draw.line([(px, y_offset + height - margin_bottom), (px, y_offset + height - margin_bottom + 3)], fill=0)
        draw.text((px - 12, y_offset + height - margin_bottom + 5), f"{hour}:00", font=label_font, fill=0)

# Draw tide curve
draw_curve_graph(draw, 30, 50, 450, 320, tide_events, "GOAT ROCK TIDES (Predictions)")

# Draw stage curve
draw_curve_graph(draw, 520, 50, 450, 320, stage_events, "JENNER STAGE (Measurements)")

# Annotations
draw.text((30, img_height - 40), "Tides: Full ±5 ft (predictable)", font=label_font, fill=0)
draw.text((520, img_height - 40), "Stage: 1-6 ft (river flow affected)", font=label_font, fill=0)

img.save("d:/GitHub/tides/AMPLITUDE_COMPARISON.png")
print(f"\nSaved comparison: AMPLITUDE_COMPARISON.png")
