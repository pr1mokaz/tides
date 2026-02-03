#!/usr/bin/env python3
"""Test script to visualize the USGS Jenner stage curve in isolation."""

import math
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# Simulate the polynomial fitting function
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

# Generate sample USGS data following the pattern from the image
# The curve shows water stage rising and falling throughout the day
sample_usgs_data = [
    {"time": "12:00 AM", "minutes": 0, "stage": 2.8},      # Low point early morning
    {"time": "3:00 AM", "minutes": 180, "stage": 3.2},
    {"time": "6:00 AM", "minutes": 360, "stage": 4.5},     # Rising
    {"time": "9:00 AM", "minutes": 540, "stage": 5.55},    # Peak around 9:45
    {"time": "12:00 PM", "minutes": 720, "stage": 4.8},    # Falling after peak
    {"time": "3:00 PM", "minutes": 900, "stage": 3.5},     # Dropping
    {"time": "6:00 PM", "minutes": 1080, "stage": 2.2},    # Low point
    {"time": "9:00 PM", "minutes": 1260, "stage": 3.8},    # Rising again
    {"time": "11:30 PM", "minutes": 1410, "stage": 5.2},   # Back up
]

# Create image
width, height = 500, 300
img = Image.new("1", (width, height), 255)
draw = ImageDraw.Draw(img)

# Load fonts
try:
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except:
    title_font = label_font = ImageFont.load_default()

# Draw title
draw.text((10, 10), "USGS Jenner Stage Curve Test", font=title_font, fill=0)

# Graph parameters
margin_left = 40
margin_right = 20
margin_top = 40
margin_bottom = 40

graph_width = width - margin_left - margin_right
graph_height = height - margin_top - margin_bottom

# Scale: -2 to 8 ft (same as main graph)
h_min, h_max = -2, 8
h_range = h_max - h_min

# Draw axis box
draw.rectangle(
    (margin_left, margin_top, width - margin_right, height - margin_bottom),
    outline=0, fill=255
)

# Parse sample data into events
events = [(d["minutes"], d["stage"]) for d in sample_usgs_data]
events.sort()

print("Sample USGS data points:")
for d in sample_usgs_data:
    print(f"  {d['time']:12} ({d['minutes']:4}min): {d['stage']:.2f}ft")

# Sample every 15 minutes for curve
step = 15
points = []
for t_min in range(0, 24 * 60 + 1, step):
    h = polynomial_fit_interpolate(t_min, events, degree=3)
    if h is not None:
        px = margin_left + int((t_min / 1440) * graph_width)
        py = height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
        points.append((px, py))
        
        # Clamp y to visible area
        if py < margin_top:
            py = margin_top
        elif py > height - margin_bottom:
            py = height - margin_bottom

# Draw the curve (dotted style - every 3rd point)
if len(points) > 1:
    for i in range(0, len(points) - 1, 3):
        draw.line((points[i], points[i + 1]), fill=0, width=2)

# Draw measurement points as small circles
for t_min, h in events:
    px = margin_left + int((t_min / 1440) * graph_width)
    py = height - margin_bottom - int(((h - h_min) / h_range) * graph_height)
    # Draw small circle for measurement
    r = 2
    draw.ellipse((px-r, py-r, px+r, py+r), fill=0)

# Draw y-axis labels
for h_label in [-2, 0, 2, 4, 6, 8]:
    py = height - margin_bottom - int(((h_label - h_min) / h_range) * graph_height)
    draw.line((margin_left - 3, py, margin_left, py), fill=0, width=1)
    label_text = str(h_label)
    label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
    label_width = label_bbox[2] - label_bbox[0]
    draw.text((margin_left - 10 - label_width, py - 4), label_text, font=label_font, fill=0)

# Draw x-axis time labels
for h_label in [0, 4, 8, 12, 16, 20]:
    t_min = h_label * 60
    px = margin_left + int((t_min / 1440) * graph_width)
    draw.line((px, height - margin_bottom, px, height - margin_bottom + 3), fill=0, width=1)
    label = f"{h_label}:00"
    draw.text((px - 12, height - margin_bottom + 5), label, font=label_font, fill=0)

# Draw legend
draw.text((10, height - 25), "Solid curve = polynomial fit | Dots = measurements", font=label_font, fill=0)

# Save image
img.save("d:/GitHub/tides/usgs_curve_test.png")
print("\nSaved visualization to: d:/GitHub/tides/usgs_curve_test.png")

# Also print interpolated values at various times for debugging
print("\nInterpolated values at key times:")
for h in [0, 6, 12, 18, 24]:
    t_min = h * 60
    value = polynomial_fit_interpolate(t_min, events, degree=3)
    if value:
        print(f"  {h:2d}:00 ({t_min:4d}min): {value:.2f}ft")
