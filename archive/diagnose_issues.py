#!/usr/bin/env python3
"""
Diagnose flat lines and phase issues by visualizing exact data from tides.json
"""

import json
import math
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

def parse_time(t_str):
    """Parse time string to minutes since midnight"""
    if "AM" in t_str or "PM" in t_str:
        dt = datetime.strptime(t_str, "%I:%M %p")
    else:
        dt = datetime.strptime(t_str.strip("0"), "%H:%M")
    return dt.hour * 60 + dt.minute

def half_sine_interpolate(t_min, events):
    """Interpolate using half-sine"""
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
    """Interpolate using polynomial fitting"""
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

# Load current tides.json
with open('tides.json', 'r') as f:
    data = json.load(f)

yesterday = "2026-02-01"
today = "2026-02-02"
tomorrow = "2026-02-03"

print("=" * 80)
print("DIAGNOSING FLAT LINES AND PHASE ISSUES")
print("=" * 80)

# Check what data exists
print(f"\n1. DATA INVENTORY IN tides.json:")
print(f"   Yesterday ({yesterday}) Goat Rock tides: {len(data.get('goat_rock', {}).get(yesterday, []))} points")
print(f"   Today ({today}) Goat Rock tides: {len(data.get('goat_rock', {}).get(today, []))} points")
print(f"   Tomorrow ({tomorrow}) Goat Rock tides: {len(data.get('goat_rock', {}).get(tomorrow, []))} points")
print(f"   Today ({today}) Stage history: {len(data.get('jenner_stage_history', {}).get(today, []))} points")
print(f"   Yesterday ({yesterday}) Stage history: {len(data.get('jenner_stage_history', {}).get(yesterday, []))} points")

# Get tides
goat_rock_yesterday = data.get('goat_rock', {}).get(yesterday, [])
goat_rock_today = data.get('goat_rock', {}).get(today, [])
goat_rock_tomorrow = data.get('goat_rock', {}).get(tomorrow, [])

estuary_yesterday = data.get('estuary', {}).get(yesterday, [])
estuary_today = data.get('estuary', {}).get(today, [])
estuary_tomorrow = data.get('estuary', {}).get(tomorrow, [])

# Get stage
stage_yesterday = data.get('jenner_stage_history', {}).get(yesterday, [])
stage_today = data.get('jenner_stage_history', {}).get(today, [])
stage_tomorrow = data.get('jenner_stage_history', {}).get(tomorrow, [])

# Print raw data
print(f"\n2. RAW GOAT ROCK TIDAL DATA:")
print(f"   Yesterday: {goat_rock_yesterday}")
print(f"   Today: {goat_rock_today}")
print(f"   Tomorrow: {goat_rock_tomorrow}")

print(f"\n3. RAW ESTUARY TIDAL DATA:")
print(f"   Yesterday: {estuary_yesterday}")
print(f"   Today: {estuary_today}")
print(f"   Tomorrow: {estuary_tomorrow}")

print(f"\n4. RAW STAGE DATA (first 5 and last 5):")
if stage_today:
    print(f"   Today first 5: {stage_today[:5]}")
    print(f"   Today last 5: {stage_today[-5:]}")

# Parse events
def parse_tides(tides, offset=0):
    events = []
    for order, time_str, height_str in tides:
        t_min = parse_time(time_str) + offset
        h = float(height_str.replace("ft", "").strip())
        events.append((t_min, h))
    return events

def parse_stage(stage_list, offset=0):
    return [(m["minutes"] + offset, m["stage"]) for m in stage_list]

# Combine three days
tide_events = sorted(
    parse_tides(goat_rock_yesterday, -1440) + 
    parse_tides(goat_rock_today, 0) + 
    parse_tides(goat_rock_tomorrow, 1440)
)
estuary_events = sorted(
    parse_tides(estuary_yesterday, -1440) + 
    parse_tides(estuary_today, 0) + 
    parse_tides(estuary_tomorrow, 1440)
)
stage_events = sorted(
    parse_stage(stage_yesterday, -1440) + 
    parse_stage(stage_today, 0) + 
    parse_stage(stage_tomorrow, 1440)
)

print(f"\n5. COMBINED TIDE EVENTS (with day offsets):")
print(f"   Total Goat Rock events: {len(tide_events)}")
if tide_events:
    print(f"   First 3: {tide_events[:3]}")
    print(f"   Last 3: {tide_events[-3:]}")

print(f"\n   Total Estuary events: {len(estuary_events)}")
if estuary_events:
    print(f"   First 3: {estuary_events[:3]}")
    print(f"   Last 3: {estuary_events[-3:]}")

print(f"\n   Total Stage events: {len(stage_events)}")
if stage_events:
    print(f"   First 3: {stage_events[:3]}")
    print(f"   Last 3: {stage_events[-3:]}")

# Check interpolation at key times
print(f"\n6. INTERPOLATION TEST (0:00-12:00 today):")
print(f"   Time     | Goat Rock | Estuary | Stage")
print(f"   " + "-" * 40)
for hour in range(0, 13, 1):
    t_min = hour * 60
    gr = half_sine_interpolate(t_min, tide_events)
    est = half_sine_interpolate(t_min, estuary_events)
    stg = polynomial_fit_interpolate(t_min, stage_events)
    
    gr_str = f"{gr:>6.2f} ft" if gr is not None else "NO DATA"
    est_str = f"{est:>6.2f} ft" if est is not None else "NO DATA"
    stg_str = f"{stg:>6.2f} ft" if stg is not None else "NO DATA"
    
    print(f"   {hour:2d}:00   | {gr_str} | {est_str} | {stg_str}")

# Create visualization
print(f"\n7. CREATING DIAGNOSTIC GRAPH...")

img_width, img_height = 1200, 500
img = Image.new("1", (img_width, img_height), 255)
draw = ImageDraw.Draw(img)

try:
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
    label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
except:
    title_font = label_font = ImageFont.load_default()

draw.text((20, 10), f"DIAGNOSTIC: Flat Lines & Phase Issues - Today is {today}", font=title_font, fill=0)

# Draw main graph
margin_left = 60
margin_right = 20
margin_top = 40
margin_bottom = 60

graph_width = img_width - margin_left - margin_right
graph_height = img_height - margin_top - margin_bottom

h_min, h_max = -2, 8
h_range = h_max - h_min

# Background
draw.rectangle((margin_left, margin_top, img_width - margin_right, img_height - margin_bottom), 
               outline=0, fill=255)

# Draw curves for today only (0 to 1440)
def draw_curve(events, color_line=0, label="", style="solid"):
    points = []
    for t_min in range(0, 1441, 10):
        h = half_sine_interpolate(t_min, events)
        if h is not None:
            px = margin_left + int((t_min / 1440) * graph_width)
            py = img_height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
            points.append((px, py))
    
    if len(points) > 1:
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            if style == "solid":
                draw.line([(x1, y1), (x2, y2)], fill=0, width=2)
            elif style == "dashed":
                if (i % 3) == 0:
                    draw.line([(x1, y1), (x2, y2)], fill=0, width=2)
    
    # Draw points
    for t_min, h in events:
        if 0 <= t_min <= 1440:
            px = margin_left + int((t_min / 1440) * graph_width)
            py = img_height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
            r = 3
            draw.ellipse((px-r, py-r, px+r, py+r), fill=0)

def draw_stage_curve(events):
    points = []
    for t_min in range(0, 1441, 10):
        h = polynomial_fit_interpolate(t_min, events)
        if h is not None:
            px = margin_left + int((t_min / 1440) * graph_width)
            py = img_height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
            points.append((px, py))
    
    if len(points) > 1:
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            draw.line([(x1, y1), (x2, y2)], fill=0, width=2)
    
    # Draw points
    for t_min, h in events:
        if 0 <= t_min <= 1440:
            px = margin_left + int((t_min / 1440) * graph_width)
            py = img_height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
            draw.ellipse((px-2, py-2, px+2, py+2), fill=128)

# Draw curves
draw_curve(tide_events, label="Goat Rock Tides", style="solid")
draw_curve(estuary_events, label="Estuary Tides", style="dashed")
draw_stage_curve(stage_events)

# Y-axis labels
for h_label in [-2, 0, 2, 4, 6, 8]:
    py = img_height - margin_bottom - int(((h_label - h_min) / h_range) * graph_height)
    draw.line([(margin_left - 5, py), (margin_left, py)], fill=0, width=1)
    draw.text((10, py - 5), f"{h_label}ft", font=label_font, fill=0)

# X-axis labels
for hour in [0, 6, 12, 18, 24]:
    t_min = hour * 60
    px = margin_left + int((t_min / 1440) * graph_width)
    draw.line([(px, img_height - margin_bottom), (px, img_height - margin_bottom + 5)], fill=0)
    draw.text((px - 15, img_height - margin_bottom + 8), f"{hour}:00", font=label_font, fill=0)

# Legend
draw.text((margin_left, img_height - 35), 
         "Solid=Goat Rock (tides)  Dashed=Estuary (tides)  Gray dots=Stage (measured)", 
         font=label_font, fill=0)
draw.text((margin_left, img_height - 20), 
         "CHECK: Tides should peak at 10-12 AM, Stage peaks at 4 AM = PHASE MISMATCH", 
         font=label_font, fill=0)

img.save("DIAGNOSTIC_FLAT_LINES.png")
print(f"   Saved: DIAGNOSTIC_FLAT_LINES.png")

print("\n" + "=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("1. Check if Stage peaks at 4 AM = data mismatch with reality")
print("2. Check if any section shows completely flat = interpolation bug")
print("3. Are there gaps in the data (missing data points)?")
print("=" * 80)
