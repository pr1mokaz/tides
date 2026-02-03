#!/usr/bin/env python3
"""Create before/after comparison showing the day boundary fix."""

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

def draw_graph_section(draw, x_offset, y_offset, width, height, events, use_boundary_fix=False, title=""):
    """Draw 0:00-6:00 time window showing flat line (before) or continuous curve (after)."""
    
    margin_left = 40
    margin_right = 10
    margin_top = 20
    margin_bottom = 30
    
    graph_width = width - margin_left - margin_right
    graph_height = height - margin_top - margin_bottom
    
    h_min, h_max = -2, 8
    h_range = h_max - h_min
    
    # Draw background and border
    draw.rectangle((x_offset, y_offset, x_offset + width, y_offset + height), outline=0, fill=255)
    draw.rectangle((x_offset + margin_left, y_offset + margin_top, x_offset + width - margin_right, 
                   y_offset + height - margin_bottom), outline=0, fill=255)
    
    # Title
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
    except:
        title_font = label_font = ImageFont.load_default()
    
    draw.text((x_offset + 5, y_offset + 3), title, font=title_font, fill=0)
    
    # For the first graph (before fix): only use today's data
    # For the second graph (after fix): use yesterday + today data
    if use_boundary_fix:
        # Include yesterday's data offset by -1440 minutes
        combined = events
    else:
        # Only today's data (0 to 1440 minutes)
        combined = [(t, h) for t, h in events if t >= 0]
    
    # Draw curve for 0:00 to 6:00 window (0 to 360 minutes)
    points = []
    for t_min in range(0, 361, 10):
        h = polynomial_fit_interpolate(t_min, combined, degree=3) if combined else None
        if h is not None:
            px = x_offset + margin_left + int((t_min / 360) * graph_width)
            py = y_offset + height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
            points.append((px, py))
    
    # Draw curve
    if len(points) > 1:
        for i in range(len(points) - 1):
            draw.line([(points[i][0], points[i][1]), (points[i + 1][0], points[i + 1][1])], fill=0, width=2)
    
    # Draw measurement points
    for t_min, h in combined:
        if 0 <= t_min <= 360:  # Only show points in the 0-6 hour window
            px = x_offset + margin_left + int((t_min / 360) * graph_width)
            py = y_offset + height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
            r = 2
            draw.ellipse((px-r, py-r, px+r, py+r), fill=0)
    
    # Y-axis labels
    for h_label in [0, 4, 8]:
        py = y_offset + height - margin_bottom - int(((h_label - h_min) / h_range) * graph_height)
        draw.line([(x_offset + margin_left - 2, py), (x_offset + margin_left, py)], fill=0, width=1)
        draw.text((x_offset + 10, py - 3), f"{h_label}ft", font=label_font, fill=0)
    
    # X-axis labels (0:00, 2:00, 4:00, 6:00)
    for hour in [0, 2, 4, 6]:
        t_min = hour * 60
        px = x_offset + margin_left + int((t_min / 360) * graph_width)
        draw.line([(px, y_offset + height - margin_bottom), (px, y_offset + height - margin_bottom + 2)], fill=0, width=1)
        draw.text((px - 8, y_offset + height - margin_bottom + 4), f"{hour}:00", font=label_font, fill=0)

# Load data
with open('d:/GitHub/tides/tides.json', 'r') as f:
    data = json.load(f)

today = "2026-02-02"
yesterday = "2026-02-01"

# Get measurements
yesterday_jenner = data.get("jenner_stage_history", {}).get(yesterday, [])
today_jenner = data.get("jenner_stage_history", {}).get(today, [])

# Parse into events with day offsets
def parse_stage(stage_list, offset):
    return [(m["minutes"] + offset, m["stage"]) for m in stage_list]

yesterday_events = parse_stage(yesterday_jenner, -1440)
today_events = parse_stage(today_jenner, 0)
combined_events = sorted(yesterday_events + today_events)

# Create side-by-side comparison
img_width, img_height = 900, 300
img = Image.new("1", (img_width, img_height), 255)
draw = ImageDraw.Draw(img)

# Title
try:
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
except:
    title_font = ImageFont.load_default()

draw.text((20, 10), "EARLY MORNING WINDOW (0:00 to 6:00) - BEFORE vs AFTER FIX", font=title_font, fill=0)

# Before: only today's data
draw_graph_section(draw, 20, 35, 410, 240, today_events, use_boundary_fix=False, 
                   title="BEFORE: Only today's data (flat 0:00-6:00)")

# After: yesterday + today data
draw_graph_section(draw, 470, 35, 410, 240, combined_events, use_boundary_fix=True,
                   title="AFTER: Yesterday + today (smooth curve)")

# Dividing line
draw.line([(450, 35), (450, 275)], fill=0, width=1)

# Save
img.save("d:/GitHub/tides/BEFORE_AFTER_BOUNDARY_FIX.png")
print("Saved: BEFORE_AFTER_BOUNDARY_FIX.png")
print("\nComparison:")
print(f"  Left (BEFORE):  Shows flat line 0:00-6:00 (no data)")
print(f"  Right (AFTER):  Shows smooth curve 0:00-6:00 (from yesterday's trend)")
