#!/usr/bin/env python3
"""
Test why stage interpolation returns NO DATA
"""

import json
import math

def polynomial_fit_interpolate(t_min, events, degree=3):
    """Test version with debug output"""
    print(f"    poly_interpolate called with t_min={t_min}, {len(events)} events")
    
    if not events or len(events) < 2:
        print(f"      -> NO DATA (not enough events)")
        return None
    
    # Before first or after last
    if t_min < events[0][0]:
        print(f"      -> BEFORE FIRST ({t_min} < {events[0][0]})")
        return events[0][1]
    if t_min > events[-1][0]:
        print(f"      -> AFTER LAST ({t_min} > {events[-1][0]})")
        return events[-1][1]
    
    try:
        import numpy as np
        times = np.array([e[0] for e in events])
        values = np.array([e[1] for e in events])
        
        actual_degree = min(degree, len(events) - 1)
        print(f"      -> Fitting degree={actual_degree}, time range {times[0]} to {times[-1]}")
        coeffs = np.polyfit(times, values, actual_degree)
        poly = np.poly1d(coeffs)
        result = float(poly(t_min))
        print(f"      -> RESULT: {result:.2f} ft")
        return result
    except Exception as e:
        print(f"      -> EXCEPTION: {e}")
        return None

# Load current tides.json
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

print(f"Total stage events: {len(all_events_jenner)}")
print(f"First 3: {all_events_jenner[:3]}")
print(f"Last 3: {all_events_jenner[-3:]}")
print()

# Now test interpolation
all_events_jenner.sort()
print(f"After sort - First 3: {all_events_jenner[:3]}")
print()

print("Testing interpolation at key times:")
for hour in [0, 1, 2, 4, 6, 10, 12]:
    t_min = hour * 60
    print(f"\nHour {hour}:00 (t_min={t_min}):")
    h = polynomial_fit_interpolate(t_min, all_events_jenner, degree=3)
    if h is not None:
        print(f"  FINAL: {h:.2f} ft")
    else:
        print(f"  FINAL: NO DATA")
