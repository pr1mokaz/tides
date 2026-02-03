#!/usr/bin/env python3
"""Test the complete display with sample data including the third USGS curve."""

import os
import sys
import json
import math
from datetime import date, datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# ========== Function Definitions (from display_eink.py) ==========

def load_fonts():
    try:
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        section_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        small_text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    except:
        header_font = section_font = text_font = small_text_font = ImageFont.load_default()
    return header_font, section_font, text_font, small_text_font

def time_str_to_minutes(time_str):
    """Convert 'HH:MM' or 'H:MM' or '2:30 PM' to minutes since midnight."""
    try:
        if "AM" in time_str or "PM" in time_str:
            dt = datetime.strptime(time_str, "%I:%M %p")
        else:
            dt = datetime.strptime(time_str.lstrip("0"), "%H:%M")
        return dt.hour * 60 + dt.minute
    except:
        return None

def linear_interpolate(t_min, events):
    """Given a time in minutes and a list of (time_min, value) tuples,
    interpolate linearly between points. Returns value or None.
    """
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

def polynomial_fit_interpolate(t_min, events, degree=3):
    """Given a time in minutes and a list of (time_min, value) tuples,
    fit a polynomial and interpolate. Returns value or None.
    """
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

def half_sine_interpolate(t_min, events):
    """Given a time in minutes and a list of (time_min, height) tuples,
    interpolate using half-sine segments. Returns height or None.
    """
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

def draw_tide_waveform(draw, x, y, width, height, prior_tides_gr, today_tides_gr, next_tides_gr, prior_tides_est, today_tides_est, next_tides_est, prior_jenner_stage_history, today_jenner_stage_history, next_jenner_stage_history, text_font, small_text_font):
    """Draw waveform visualization with three curves."""
    
    def parse_tides(tides, day_offset_mins):
        events = []
        for label, time_str, height_str in tides:
            t_min = time_str_to_minutes(time_str)
            h_val = float(height_str.replace("ft", "").strip())
            if t_min is not None:
                events.append((t_min + day_offset_mins, h_val))
        return events
    
    def parse_stage_history(stage_list, day_offset_mins):
        events = []
        if stage_list:
            for measurement in stage_list:
                t_min = measurement.get("minutes")
                stage = measurement.get("stage")
                if t_min is not None and stage is not None:
                    events.append((t_min + day_offset_mins, float(stage)))
        return events
    
    all_events_gr = []
    all_events_gr.extend(parse_tides(prior_tides_gr, -24*60))
    all_events_gr.extend(parse_tides(today_tides_gr, 0))
    all_events_gr.extend(parse_tides(next_tides_gr, 24*60))
    
    all_events_est = []
    all_events_est.extend(parse_tides(prior_tides_est, -24*60))
    all_events_est.extend(parse_tides(today_tides_est, 0))
    all_events_est.extend(parse_tides(next_tides_est, 24*60))
    
    all_events_jenner = []
    all_events_jenner.extend(parse_stage_history(prior_jenner_stage_history, -24*60))
    all_events_jenner.extend(parse_stage_history(today_jenner_stage_history, 0))
    all_events_jenner.extend(parse_stage_history(next_jenner_stage_history, 24*60))
    
    if not all_events_gr or len(all_events_gr) < 2 or not all_events_est or len(all_events_est) < 2:
        draw.text((x, y), "Insufficient tide data", font=text_font, fill=0)
        return
    
    all_events_gr.sort()
    all_events_est.sort()
    if all_events_jenner:
        all_events_jenner.sort()
    
    h_min, h_max = -2, 8
    h_range = h_max - h_min
    
    margin_left = 12
    margin_right = 3
    margin_top = 3
    margin_bottom = 12
    
    graph_width = width - margin_left - margin_right
    graph_height = height - margin_top - margin_bottom
    
    step = 15
    points_gr = []
    points_est = []
    points_jenner = []
    
    for t_min in range(0, 24 * 60 + 1, step):
        h_gr = half_sine_interpolate(t_min, all_events_gr)
        h_est = half_sine_interpolate(t_min, all_events_est)
        if h_gr is not None:
            px = x + margin_left + int((t_min / 1440) * graph_width)
            py_gr = y + height - margin_bottom - int(((h_gr - h_min) / h_range) * graph_height)
            points_gr.append((px, py_gr))
        if h_est is not None:
            px = x + margin_left + int((t_min / 1440) * graph_width)
            py_est = y + height - margin_bottom - int(((h_est - h_min) / h_range) * graph_height)
            points_est.append((px, py_est))
        if all_events_jenner and len(all_events_jenner) >= 2:
            h_jenner = polynomial_fit_interpolate(t_min, all_events_jenner, degree=3)
            if h_jenner is not None:
                px = x + margin_left + int((t_min / 1440) * graph_width)
                py_jenner = y + height - margin_bottom - int(((h_jenner - h_min) / h_range) * graph_height)
                points_jenner.append((px, py_jenner))
    
    draw.rectangle((x + margin_left, y + margin_top, x + width - margin_right, y + height - margin_bottom), outline=0, fill=255)
    
    if len(points_gr) > 1:
        for i in range(len(points_gr) - 1):
            draw.line((points_gr[i], points_gr[i + 1]), fill=0, width=1)
    
    if len(points_est) > 1:
        for i in range(0, len(points_est) - 1, 2):
            draw.line((points_est[i], points_est[i + 1]), fill=0, width=1)
    
    if len(points_jenner) > 1:
        print(f"Drawing Jenner stage curve with {len(points_jenner)} points")
        for i in range(0, len(points_jenner) - 1, 3):
            draw.line((points_jenner[i], points_jenner[i + 1]), fill=0, width=1)
    else:
        print(f"WARNING: Not enough Jenner points ({len(points_jenner)}) to draw curve")
    
    for h_label in [-2, 0, 2, 4, 6, 8]:
        py = y + height - margin_bottom - int(((h_label - h_min) / h_range) * graph_height)
        draw.line((x + margin_left - 2, py, x + margin_left, py), fill=0, width=1)
        label_text = str(h_label)
        label_bbox = draw.textbbox((0, 0), label_text, font=small_text_font)
        label_width = label_bbox[2] - label_bbox[0]
        draw.text((x + margin_left - 4 - label_width, py - 2), label_text, font=small_text_font, fill=0)
    
    for h_label in [4, 8, 12, 16, 20]:
        t_min = h_label * 60
        px = x + margin_left + int((t_min / 1440) * graph_width)
        py = y + height - margin_bottom + 1
        draw.line((px, y + height - margin_bottom, px, y + height - margin_bottom + 2), fill=0, width=1)
        label = f"{h_label}:00"
        draw.text((px - 8, py), label, font=small_text_font, fill=0)

# ========== Load Data and Render ==========

with open('d:/GitHub/tides/tides.json', 'r') as f:
    data = json.load(f)

# Portrait settings
WIDTH = 300
HEIGHT = 400

img = Image.new("1", (WIDTH, HEIGHT), 255)
draw = ImageDraw.Draw(img)
header_font, section_font, text_font, small_text_font = load_fonts()

# Header
draw.rectangle((0, 0, WIDTH, 28), fill=0)
date_str = "Feb 02, 2026"  # Using the simulation date
bbox = draw.textbbox((0, 0), f"TIDES - {date_str}", font=header_font)
draw.text(((WIDTH-(bbox[2]-bbox[0]))//2, 4), f"TIDES - {date_str}", font=header_font, fill=255)

today_key = "2026-02-02"
bodega_tides = data.get("bodega_tides", {}).get(today_key, [])
fort_ross_tides = data.get("fort_ross", {}).get(today_key, [])
goat_rock_tides = data.get("goat_rock", {}).get(today_key, [])
estuary_tides = data.get("estuary", {}).get(today_key, [])

# Only draw the graph section
draw.text((10, 260), "TIDE CURVES", font=section_font, fill=0)
draw.text((130, 262), "(Goat Rock, Estuary & Stage)", font=small_text_font, fill=0)

yesterday_key = "2026-02-01"
tomorrow_key = "2026-02-03"
yesterday_tides_gr = data.get("goat_rock", {}).get(yesterday_key, [])
tomorrow_tides_gr = data.get("goat_rock", {}).get(tomorrow_key, [])
yesterday_tides_est = data.get("estuary", {}).get(yesterday_key, [])
tomorrow_tides_est = data.get("estuary", {}).get(tomorrow_key, [])

# Get Jenner stage history for prior, today, and next day
yesterday_jenner_stage = data.get("jenner_stage_history", {}).get(yesterday_key, [])
today_jenner_stage = data.get("jenner_stage_history", {}).get(today_key, [])
tomorrow_jenner_stage = data.get("jenner_stage_history", {}).get(tomorrow_key, [])

draw_tide_waveform(draw, 10, 275, WIDTH-20, 120, yesterday_tides_gr, goat_rock_tides, tomorrow_tides_gr,
                   yesterday_tides_est, estuary_tides, tomorrow_tides_est, 
                   yesterday_jenner_stage, today_jenner_stage, tomorrow_jenner_stage, text_font, small_text_font)

# Save
img.save("d:/GitHub/tides/display_test_with_usgs.png")
print("Saved: d:/GitHub/tides/display_test_with_usgs.png")
