#!/usr/bin/env python3
"""
Sample generator: stitch half-sine segments between tide extrema and write CSV samples.
Produces `sample_tides.csv` in the working directory.
"""
import csv
import math
from datetime import datetime


def time_to_minutes(tstr):
    h, m = map(int, tstr.split(":"))
    return h * 60 + m


def minutes_to_time(m):
    h = (m // 60) % 24
    mm = m % 60
    return f"{h:02d}:{mm:02d}"


def half_sine(t, t1, t2, h1, h2):
    """Compute half-sine interpolation between (t1,h1) and (t2,h2).
    t, t1, t2 in minutes; returns level.
    """
    if t2 == t1:
        return h1
    m = 0.5 * (h1 + h2)
    a = 0.5 * (h2 - h1)
    frac = (t - t1) / (t2 - t1)
    theta = math.pi * frac - math.pi / 2
    return m + a * math.sin(theta)


def sample_tides(events, step=10, deviation=0.0, start_min=None, end_min=None):
    """events: list of ("HH:MM", height)
    returns list of (time_str, minutes, predicted, displayed)
    """
    ev = [(time_to_minutes(ts), float(h)) for ts, h in events]
    ev.sort()

    if start_min is None:
        start_min = ev[0][0]
    if end_min is None:
        end_min = ev[-1][0]

    rows = []
    # for each sample minute, find the containing segment
    for m in range(start_min, end_min + 1, step):
        # before first event
        if m <= ev[0][0]:
            pred = ev[0][1]
        # after last event
        elif m >= ev[-1][0]:
            pred = ev[-1][1]
        else:
            # find i such that ev[i][0] <= m < ev[i+1][0]
            for i in range(len(ev) - 1):
                t1, h1 = ev[i]
                t2, h2 = ev[i + 1]
                if t1 <= m <= t2:
                    pred = half_sine(m, t1, t2, h1, h2)
                    break
        disp = pred + deviation
        rows.append((minutes_to_time(m), m, round(pred, 3), round(disp, 3)))
    return rows


if __name__ == '__main__':
    # Sample extrema (from discussion)
    events = [
        ("02:00", 0.5),
        ("08:00", 5.0),
        ("14:00", 1.0),
        ("20:00", 4.5),
    ]
    step = 10  # minutes
    deviation = 0.4

    # Sample from 00:00 to 23:50 so Excel can plot a full day
    start_min = 0
    end_min = 23 * 60 + 50

    samples = sample_tides(events, step=step, deviation=0.0, start_min=start_min, end_min=end_min)

    # Write predicted-only CSV
    out_pred = 'sample_tides_predicted.csv'
    with open(out_pred, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Time','Minute','Predicted'])
        w.writerows([(t, m, p) for (t,m,p,_) in samples])

    # Write displayed (with deviation) CSV
    out_disp = 'sample_tides_displayed.csv'
    with open(out_disp, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Time','Minute','Predicted','Displayed'])
        w.writerows(samples)

    print(f"Wrote {out_pred} and {out_disp} ({len(samples)} samples, step={step}min)")
