#!/usr/bin/env python3
"""Test if tides are properly interpolating across yesterday/today boundary."""

import math
import json

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

def parse_time(t_str):
    from datetime import datetime
    if "AM" in t_str or "PM" in t_str:
        dt = datetime.strptime(t_str, "%I:%M %p")
    else:
        dt = datetime.strptime(t_str.strip("0"), "%H:%M")
    return dt.hour * 60 + dt.minute

with open('d:/GitHub/tides/tides.json', 'r') as f:
    data = json.load(f)

today = "2026-02-02"
yesterday = "2026-02-01"

# Get yesterday and today tides
gr_yesterday = data.get("goat_rock", {}).get(yesterday, [])
gr_today = data.get("goat_rock", {}).get(today, [])

print("YESTERDAY (2026-02-01) Goat Rock tides:")
for order, time_str, height_str in gr_yesterday:
    time_minutes = parse_time(time_str)
    print(f"  {order:>6} {time_str:>10} ({time_minutes:>4} min) = {height_str:>5}")

print("\nTODAY (2026-02-02) Goat Rock tides:")
for order, time_str, height_str in gr_today:
    time_minutes = parse_time(time_str)
    print(f"  {order:>6} {time_str:>10} ({time_minutes:>4} min) = {height_str:>5}")

# Now combine with offsets like the render function does
def parse_tides(tides, offset=0):
    events = []
    for order, time_str, height_str in tides:
        t_min = parse_time(time_str) + offset
        h = float(height_str.replace("ft", "").strip())
        events.append((t_min, h))
    return events

all_events = sorted(
    parse_tides(gr_yesterday, -1440) + parse_tides(gr_today, 0)
)

print("\nCOMBINED WITH OFFSETS:")
for t_min, h in all_events:
    date = "YESTERDAY" if t_min < 0 else "TODAY" if t_min <= 1440 else "TOMORROW"
    display_time = t_min % 1440
    hour = display_time // 60
    minute = display_time % 60
    print(f"  {date:>10} t={t_min:>5} min  ({hour}:{minute:02d}) = {h:>5.1f} ft")

print("\nINTERPOLATION TEST (0:00 to 6:00 boundary):")
for t_min in [0, 60, 120, 180, 240, 300, 360]:
    h = half_sine_interpolate(t_min, all_events)
    hour = t_min // 60
    minute = t_min % 60
    if h is not None:
        print(f"  {hour}:{minute:02d} ({t_min:>4} min) = {h:>5.2f} ft")
    else:
        print(f"  {hour}:{minute:02d} ({t_min:>4} min) = NO DATA")
