#!/usr/bin/env python3
"""Create a comparison image showing the graph with and without the third curve."""

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

def draw_graph(draw, x_offset, y_offset, width, height, goat_events, estuary_events, jenner_events, show_jenner=True, title=""):
    """Draw a single graph. If show_jenner=False, only draws first two curves."""
    
    margin_left = 40
    margin_right = 10
    margin_top = 20
    margin_bottom = 30
    
    graph_width = width - margin_left - margin_right
    graph_height = height - margin_top - margin_bottom
    
    h_min, h_max = -2, 8
    h_range = h_max - h_min
    
    # Draw background and box
    draw.rectangle((x_offset, y_offset, x_offset + width, y_offset + height), outline=0, fill=255)
    draw.rectangle((x_offset + margin_left, y_offset + margin_top, x_offset + width - margin_right, y_offset + height - margin_bottom), outline=0, fill=255)
    
    # Title
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
    except:
        title_font = ImageFont.load_default()
    draw.text((x_offset + 5, y_offset + 2), title, font=title_font, fill=0)
    
    # Sample and draw curves
    step = 12
    points_gr = []
    points_est = []
    points_jen = []
    
    for t_min in range(0, 1441, step):
        h_gr = half_sine_interpolate(t_min, goat_events)
        h_est = half_sine_interpolate(t_min, estuary_events)
        
        if h_gr:
            px = x_offset + margin_left + int((t_min / 1440) * graph_width)
            py = y_offset + height - margin_bottom - int(((h_gr - h_min) / h_range) * graph_height)
            points_gr.append((px, py))
        if h_est:
            px = x_offset + margin_left + int((t_min / 1440) * graph_width)
            py = y_offset + height - margin_bottom - int(((h_est - h_min) / h_range) * graph_height)
            points_est.append((px, py))
        
        if show_jenner and jenner_events:
            h_jen = polynomial_fit_interpolate(t_min, jenner_events, degree=3)
            if h_jen:
                px = x_offset + margin_left + int((t_min / 1440) * graph_width)
                py = y_offset + height - margin_bottom - int(((h_jen - h_min) / h_range) * graph_height)
                points_jen.append((px, py))
    
    # Draw Goat Rock (solid)
    if len(points_gr) > 1:
        for i in range(len(points_gr) - 1):
            draw.line([(points_gr[i][0], points_gr[i][1]), (points_gr[i + 1][0], points_gr[i + 1][1])], fill=0, width=1)
    
    # Draw Estuary (dashed)
    if len(points_est) > 1:
        for i in range(0, len(points_est) - 1, 2):
            draw.line([(points_est[i][0], points_est[i][1]), (points_est[i + 1][0], points_est[i + 1][1])], fill=0, width=1)
    
    # Draw Jenner if requested
    if show_jenner and len(points_jen) > 1:
        for i in range(0, len(points_jen) - 1, 3):
            draw.line([(points_jen[i][0], points_jen[i][1]), (points_jen[i + 1][0], points_jen[i + 1][1])], fill=0, width=2)
    
    # Y-axis labels
    try:
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 7)
    except:
        label_font = ImageFont.load_default()
    
    for h_label in [0, 4, 8]:
        py = y_offset + height - margin_bottom - int(((h_label - h_min) / h_range) * graph_height)
        draw.line([(x_offset + margin_left - 2, py), (x_offset + margin_left, py)], fill=0, width=1)
        draw.text((x_offset + 5, py - 3), str(h_label), font=label_font, fill=0)
    
    # X-axis labels
    for h_label in [0, 6, 12, 18, 24]:
        t_min = h_label * 60
        px = x_offset + margin_left + int((t_min / 1440) * graph_width)
        draw.line([(px, y_offset + height - margin_bottom), (px, y_offset + height - margin_bottom + 2)], fill=0, width=1)
        draw.text((px - 6, y_offset + height - margin_bottom + 3), f"{h_label}", font=label_font, fill=0)

# Load data
with open('d:/GitHub/tides/tides.json', 'r') as f:
    data = json.load(f)

today = "2026-02-02"
goat_rock = data.get("goat_rock", {}).get(today, [])
estuary = data.get("estuary", {}).get(today, [])
jenner_stage = data.get("jenner_stage_history", {}).get(today, [])

def parse_time(t_str):
    if "AM" in t_str or "PM" in t_str:
        dt = datetime.strptime(t_str, "%I:%M %p")
    else:
        dt = datetime.strptime(t_str.strip("0"), "%H:%M")
    return dt.hour * 60 + dt.minute

goat_events = [(parse_time(t), float(h.replace("ft", "").strip())) for _, t, h in goat_rock]
estuary_events = [(parse_time(t), float(h.replace("ft", "").strip())) for _, t, h in estuary]
jenner_events = [(m["minutes"], m["stage"]) for m in jenner_stage]

# Create comparison image
img_width, img_height = 1000, 300
img = Image.new("1", (img_width, img_height), 255)
draw = ImageDraw.Draw(img)

# Title
try:
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
except:
    title_font = ImageFont.load_default()

draw.text((10, 5), "BEFORE vs AFTER: Third Curve Addition", font=title_font, fill=0)

# Left graph: Without third curve
draw_graph(draw, 10, 35, 480, 250, goat_events, estuary_events, jenner_events, show_jenner=False, title="BEFORE: Two curves (Goat Rock & Estuary)")

# Right graph: With third curve
draw_graph(draw, 510, 35, 480, 250, goat_events, estuary_events, jenner_events, show_jenner=True, title="AFTER: Three curves (+ Jenner Stage)")

# Dividing line
draw.line([(500, 35), (500, 285)], fill=0, width=1)

# Legend at bottom
try:
    legend_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
except:
    legend_font = ImageFont.load_default()

draw.text((20, 290), "Solid: Goat Rock  |  Dashed: Estuary  |  Dotted (thick): Jenner Stage", font=legend_font, fill=0)

img.save("d:/GitHub/tides/BEFORE_AFTER_COMPARISON.png")
print("Saved comparison image: BEFORE_AFTER_COMPARISON.png (1000x300)")
