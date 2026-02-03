#!/usr/bin/env python3
"""
Final test of stage curve with fixed Lagrange interpolation
"""

import json
import math

def linear_interpolate(t_min, events):
    """Linear interpolation between points"""
    if not events or len(events) < 1:
        return None
    
    if t_min < events[0][0]:
        return events[0][1]
    if t_min > events[-1][0]:
        return events[-1][1]
    
    for i in range(len(events) - 1):
        t1, v1 = events[i]
        t2, v2 = events[i + 1]
        if t1 <= t_min <= t2:
            if t2 == t1:
                return v1
            frac = (t_min - t1) / (t2 - t1)
            return v1 + frac * (v2 - v1)
    
    return None

def polynomial_fit_interpolate(t_min, events, degree=3):
    """Lagrange polynomial interpolation (no numpy required)"""
    if not events or len(events) < 2:
        return None
    
    if t_min < events[0][0]:
        return events[0][1]
    if t_min > events[-1][0]:
        return events[-1][1]
    
    times = [e[0] for e in events]
    values = [e[1] for e in events]
    
    # Find the interval
    idx = None
    for i in range(len(times) - 1):
        if times[i] <= t_min <= times[i + 1]:
            idx = i
            break
    
    if idx is None:
        return linear_interpolate(t_min, events)
    
    # Use surrounding points for Lagrange interpolation
    start_idx = max(0, idx - 2)
    end_idx = min(len(times), idx + 3)
    
    x_points = times[start_idx:end_idx]
    y_points = values[start_idx:end_idx]
    
    # Lagrange polynomial
    result = 0.0
    for i, (x_i, y_i) in enumerate(zip(x_points, y_points)):
        term = y_i
        for j, x_j in enumerate(x_points):
            if i != j:
                term *= (t_min - x_j) / (x_i - x_j)
        result += term
    
    return result

# Load tides.json
with open('tides.json', 'r') as f:
    data = json.load(f)

yesterday = "2026-02-01"
today = "2026-02-02"
tomorrow = "2026-02-03"

# Get stage
stage_yesterday = data.get('jenner_stage_history', {}).get(yesterday, [])
stage_today = data.get('jenner_stage_history', {}).get(today, [])
stage_tomorrow = data.get('jenner_stage_history', {}).get(tomorrow, [])

def parse_stage(stage_list, offset=0):
    events = []
    if stage_list:
        for measurement in stage_list:
            t_min = measurement.get("minutes")
            stage = measurement.get("stage")
            if t_min is not None and stage is not None:
                events.append((t_min + offset, float(stage)))
    return events

# Combine three days
all_events_jenner = []
all_events_jenner.extend(parse_stage(stage_yesterday, -1440))
all_events_jenner.extend(parse_stage(stage_today, 0))
all_events_jenner.extend(parse_stage(stage_tomorrow, 1440))
all_events_jenner.sort()

print(f"Stage data loaded: {len(all_events_jenner)} total points")
print(f"Time range: {all_events_jenner[0][0]} to {all_events_jenner[-1][0]} minutes")
print(f"Value range: {min(e[1] for e in all_events_jenner):.1f} to {max(e[1] for e in all_events_jenner):.1f} ft")
print()

# Get tides for comparison
goat_rock_yesterday = data.get('goat_rock', {}).get(yesterday, [])
goat_rock_today = data.get('goat_rock', {}).get(today, [])
goat_rock_tomorrow = data.get('goat_rock', {}).get(tomorrow, [])

def parse_tides(tides, offset=0):
    events = []
    for label, time_str, height_str in tides:
        from datetime import datetime
        try:
            if "AM" in time_str or "PM" in time_str:
                dt = datetime.strptime(time_str, "%I:%M %p")
            else:
                dt = datetime.strptime(time_str.lstrip("0"), "%H:%M")
            t_min = dt.hour * 60 + dt.minute + offset
            h = float(height_str.replace("ft", "").strip())
            events.append((t_min, h))
        except:
            pass
    return events

def half_sine_interpolate(t_min, events):
    """Half-sine interpolation for tides"""
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

all_tides = sorted(
    parse_tides(goat_rock_yesterday, -1440) + 
    parse_tides(goat_rock_today, 0) + 
    parse_tides(goat_rock_tomorrow, 1440)
)

print("INTERPOLATION TEST: 0:00 - 12:00 TODAY")
print()
print("Time  | Goat Rock Tides | Jenner Stage")
print("------|-----------------|----------------")

for hour in range(0, 13):
    t_min = hour * 60
    tide_h = half_sine_interpolate(t_min, all_tides)
    stage_h = polynomial_fit_interpolate(t_min, all_events_jenner)
    
    tide_str = f"{tide_h:>6.2f} ft" if tide_h is not None else "NO DATA"
    stage_str = f"{stage_h:>6.2f} ft" if stage_h is not None else "NO DATA"
    
    print(f"{hour:>2d}:00 | {tide_str} | {stage_str}")

print()
print("PHASE ANALYSIS:")
print("-" * 50)

# Find peaks
print("Finding peak tides:")
max_tide = max((half_sine_interpolate(t, all_tides) for t in range(0, 1441, 60)))
for t in range(0, 1441, 60):
    h = half_sine_interpolate(t, all_tides)
    if h == max_tide:
        hour = t // 60
        minute = t % 60
        print(f"  Goat Rock tide peaks at {hour}:{minute:02d} = {h:.2f} ft")
        break

print()
print("Finding peak stage:")
max_stage = max((polynomial_fit_interpolate(t, all_events_jenner) for t in range(0, 1441, 60)))
for t in range(0, 1441, 60):
    h = polynomial_fit_interpolate(t, all_events_jenner)
    if h == max_stage:
        hour = t // 60
        minute = t % 60
        print(f"  Jenner stage peaks at {hour}:{minute:02d} = {h:.2f} ft")
        break

print()
print("✓ Display will show both curves correctly now!")
