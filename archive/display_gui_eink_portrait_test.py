#!/usr/bin/env python3
"""Display GUI mock for testing on Windows (without hardware)."""
import os
import sys
import json
import time
import math
from datetime import date, datetime
from PIL import Image, ImageDraw, ImageFont

# Don't import waveshare on non-Pi systems
SKIP_HARDWARE = True

# Settings - SWAPPED FOR PORTRAIT
DATA_FILE = "tides.json"
WIDTH = 300   
HEIGHT = 400  

# ---------- Drawing Helpers ----------

def load_fonts():
    try:
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        section_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        small_text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    except:
        header_font = section_font = text_font = small_text_font = ImageFont.load_default()
    return header_font, section_font, text_font, small_text_font

def draw_station_block(draw, x, y, title, tides, section_font, text_font):
    draw.text((x, y), title, font=section_font, fill=0)
    curr_y = y + 18
    # Render up to four tide entries with right-justified alignment
    for label, t, h in tides[:4]:
        # Label at x
        draw.text((x, curr_y), label, font=text_font, fill=0)
        # Time right-justified on M of AM/PM at x+95 (moved left from x+105)
        t_bbox = draw.textbbox((0, 0), t, font=text_font)
        t_width = t_bbox[2] - t_bbox[0]
        draw.text((x + 95 - t_width, curr_y), t, font=text_font, fill=0)
        # Height right-justified on t of ft at x+135 (moved left from x+140)
        h_bbox = draw.textbbox((0, 0), h, font=text_font)
        h_width = h_bbox[2] - h_bbox[0]
        draw.text((x + 135 - h_width, curr_y), h, font=text_font, fill=0)
        curr_y += 14
    return curr_y

def draw_flow_block(draw, x, y, data, section_font, text_font):
    draw.text((x, y), "WEST RUSSIAN RIVER CONDITIONS", font=section_font, fill=0)
    curr_y = y + 18
    # Hacienda: label on left, stage/flow right-justified at x+280
    hacienda_text = f"{data.get('hacienda_stage','--')} ft {data.get('hacienda_cfs','--')}cfs"
    draw.text((x, curr_y), "Hacienda:", font=text_font, fill=0)
    h_bbox = draw.textbbox((0, 0), hacienda_text, font=text_font)
    h_width = h_bbox[2] - h_bbox[0]
    draw.text((x + 280 - h_width, curr_y), hacienda_text, font=text_font, fill=0)
    curr_y += 14
    # Jenner: label on left, stage right-justified at x+280
    jenner_text = f"{data.get('jenner_stage','--')} ft"
    draw.text((x, curr_y), "Jenner:", font=text_font, fill=0)
    j_bbox = draw.textbbox((0, 0), jenner_text, font=text_font)
    j_width = j_bbox[2] - j_bbox[0]
    draw.text((x + 280 - j_width, curr_y), jenner_text, font=text_font, fill=0)
    curr_y += 14
    curr_y += 2
    # Mouth: label on left, status right-justified at x+280
    mouth_text = data.get('river_mouth_status','UNKNOWN')
    draw.text((x, curr_y), "River Mouth Barrier Bar:", font=text_font, fill=0)
    m_bbox = draw.textbbox((0, 0), mouth_text, font=text_font)
    m_width = m_bbox[2] - m_bbox[0]
    draw.text((x + 280 - m_width, curr_y), mouth_text, font=text_font, fill=0)
    curr_y += 14

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

def half_sine_interpolate(t_min, events):
    """Given a time in minutes and a list of (time_min, height) tuples,
    interpolate using half-sine segments. Returns height or None.
    """
    if not events or len(events) < 2:
        return None
    
    # Before first or after last
    if t_min < events[0][0]:
        return events[0][1]
    if t_min > events[-1][0]:
        return events[-1][1]
    
    # Find bracketing pair
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

def draw_tide_waveform(draw, x, y, width, height, prior_tides_gr, today_tides_gr, next_tides_gr, prior_tides_est, today_tides_est, next_tides_est, text_font, small_text_font):
    """Draw waveform visualization with two curves: Goat Rock (solid) and Jenner Estuary (dashed).
    Uses prior/today/next day data to create smooth curve edges at midnight boundaries.
    Only displays today's window (0-1440 minutes).
    """
    # Parse all three days into events
    def parse_tides(tides, day_offset_mins):
        events = []
        for label, time_str, height_str in tides:
            t_min = time_str_to_minutes(time_str)
            h_val = float(height_str.replace("ft", "").strip())
            if t_min is not None:
                events.append((t_min + day_offset_mins, h_val))
        return events
    
    # Combine 3 days for Goat Rock: prior (-1440 to 0), today (0 to 1440), next (1440 to 2880)
    all_events_gr = []
    all_events_gr.extend(parse_tides(prior_tides_gr, -24*60))
    all_events_gr.extend(parse_tides(today_tides_gr, 0))
    all_events_gr.extend(parse_tides(next_tides_gr, 24*60))
    
    # Combine 3 days for Estuary: prior (-1440 to 0), today (0 to 1440), next (1440 to 2880)
    all_events_est = []
    all_events_est.extend(parse_tides(prior_tides_est, -24*60))
    all_events_est.extend(parse_tides(today_tides_est, 0))
    all_events_est.extend(parse_tides(next_tides_est, 24*60))
    
    if not all_events_gr or len(all_events_gr) < 2 or not all_events_est or len(all_events_est) < 2:
        draw.text((x, y), "Insufficient tide data", font=text_font, fill=0)
        return
    
    all_events_gr.sort()
    all_events_est.sort()
    
    # Fixed scale: -2 to 8 ft for consistent display
    h_min, h_max = -2, 8
    h_range = h_max - h_min
    
    # Margins
    margin_left = 12
    margin_right = 3
    margin_top = 3
    margin_bottom = 12
    
    graph_width = width - margin_left - margin_right
    graph_height = height - margin_top - margin_bottom
    
    # Sample every 15 minutes for smoother curve (1440 min / 96 samples)
    step = 15
    points_gr = []
    points_est = []
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
    
    # Draw axis box
    draw.rectangle((x + margin_left, y + margin_top, x + width - margin_right, y + height - margin_bottom), outline=0, fill=255)
    
    # Draw Goat Rock curve (solid line)
    if len(points_gr) > 1:
        for i in range(len(points_gr) - 1):
            draw.line((points_gr[i], points_gr[i + 1]), fill=0, width=1)
    
    # Draw Estuary curve (dashed line - every other point)
    if len(points_est) > 1:
        for i in range(0, len(points_est) - 1, 2):
            draw.line((points_est[i], points_est[i + 1]), fill=0, width=1)
    
    # Draw y-axis labels and markers (-2, 0, 2, 4, 6, 8 ft)
    for h_label in [-2, 0, 2, 4, 6, 8]:
        py = y + height - margin_bottom - int(((h_label - h_min) / h_range) * graph_height)
        # Draw tick mark
        draw.line((x + margin_left - 2, py, x + margin_left, py), fill=0, width=1)
        # Draw label right-justified with smaller font
        label_text = str(h_label)
        label_bbox = draw.textbbox((0, 0), label_text, font=small_text_font)
        label_width = label_bbox[2] - label_bbox[0]
        draw.text((x + margin_left - 4 - label_width, py - 2), label_text, font=small_text_font, fill=0)
    
    # Draw x-axis time labels (4:00, 8:00, 12:00, 16:00, 20:00)
    for h_label in [4, 8, 12, 16, 20]:
        t_min = h_label * 60
        px = x + margin_left + int((t_min / 1440) * graph_width)
        py = y + height - margin_bottom + 1
        # Draw tick mark
        draw.line((px, y + height - margin_bottom, px, y + height - margin_bottom + 2), fill=0, width=1)
        # Draw label with :00 format
        label = f"{h_label}:00"
        draw.text((px - 8, py), label, font=small_text_font, fill=0)

def render_tide_layout(data):
    # Create Portrait Image
    img = Image.new("1", (WIDTH, HEIGHT), 255) 
    draw = ImageDraw.Draw(img)
    header_font, section_font, text_font, small_text_font = load_fonts()

    # 1. Header Bar
    draw.rectangle((0, 0, WIDTH, 28), fill=0) 
    date_str = date.today().strftime("%b %d, %Y")
    today_key = date.today().strftime("%Y-%m-%d")
    bbox = draw.textbbox((0, 0), f"TIDES - {date_str}", font=header_font)
    draw.text(((WIDTH-(bbox[2]-bbox[0]))//2, 4), f"TIDES - {date_str}", font=header_font, fill=255)

    # Extract today's tides from the multi-day dicts
    bodega_tides = data.get("bodega_tides", {}).get(today_key, [])
    fort_ross_tides = data.get("fort_ross", {}).get(today_key, [])
    goat_rock_tides = data.get("goat_rock", {}).get(today_key, [])
    estuary_tides = data.get("estuary", {}).get(today_key, [])

    # 2. Block 1: Coastal (Bodega & Fort Ross side-by-side)
    draw_station_block(draw, 10, 35, "BODEGA BAY", bodega_tides, section_font, text_font)
    draw_station_block(draw, 160, 35, "FORT ROSS", fort_ross_tides, section_font, text_font)
    
    # 3. Block 2: Beach & Estuary (Goat Rock & Estuary side-by-side)
    draw_station_block(draw, 10, 110, "GOAT ROCK", goat_rock_tides, section_font, text_font)
    draw_station_block(draw, 160, 110, "JENNER ESTUARY", estuary_tides, section_font, text_font)
    
    # 4. Block 3: West Russian River Conditions (Full Width)
    draw_flow_block(draw, 10, 190, data, section_font, text_font)
    
    # 5. Block 4: Tide Waveforms (bottom) - Goat Rock & Jenner Estuary
    draw.text((10, 260), "TIDE CURVES", font=section_font, fill=0)
    draw.text((130, 262), "(Goat Rock & Estuary)", font=small_text_font, fill=0)
    # Get prior, today, and next day tides for smooth curve edges
    from datetime import timedelta
    yesterday_key = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_key = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_tides_gr = data.get("goat_rock", {}).get(yesterday_key, [])
    tomorrow_tides_gr = data.get("goat_rock", {}).get(tomorrow_key, [])
    yesterday_tides_est = data.get("estuary", {}).get(yesterday_key, [])
    tomorrow_tides_est = data.get("estuary", {}).get(tomorrow_key, [])
    draw_tide_waveform(draw, 10, 275, WIDTH-20, 120, yesterday_tides_gr, goat_rock_tides, tomorrow_tides_gr, 
                       yesterday_tides_est, estuary_tides, tomorrow_tides_est, text_font, small_text_font)

    return img

# ---------- Main Loop ----------

def main():
    if not SKIP_HARDWARE:
        print("Initializing e-Paper (Portrait)...")
        from waveshare_epd import epd4in2_V2
        epd = epd4in2_V2.EPD()
    
    last_mtime = 0
    while True:
        if os.path.exists(DATA_FILE):
            mtime = os.path.getmtime(DATA_FILE)
            if mtime > last_mtime:
                try:
                    with open(DATA_FILE, "r") as f:
                        data = json.load(f)
                    
                    print("Rendering Portrait Display...")
                    img = render_tide_layout(data)
                    
                    if not SKIP_HARDWARE:
                        epd.init()
                        epd.display(epd.getbuffer(img))
                        epd.sleep() 
                    else:
                        # For testing: save to file
                        img.save("display_output.png")
                        print("Saved to display_output.png")
                    
                    last_mtime = mtime
                    print(f"Update Complete: {time.ctime()}")
                except Exception as e:
                    print(f"Error: {e}")
                    import traceback
                    traceback.print_exc()
        
        time.sleep(60) 

if __name__ == "__main__":
    main()
