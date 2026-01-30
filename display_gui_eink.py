#!/usr/bin/env python3
import os
import sys
import json
import time
from datetime import date
from PIL import Image, ImageDraw, ImageFont

# Path to your Waveshare library
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'e-Paper/RaspberryPi_JetsonNano/python/lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd4in2_V2

# Settings
DATA_FILE = "tides.json"
WIDTH = 400
HEIGHT = 300

# ---------- Drawing Helpers ----------

def load_fonts():
    try:
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        section_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        header_font = section_font = text_font = ImageFont.load_default()
    return header_font, section_font, text_font

def draw_station_block(draw, x, y, title, tides, section_font, text_font, data=None, is_tide_area=False):
    draw.text((x, y), title, font=section_font, fill=0)
    curr_y = y + 16
    for label, t, h in tides[:3]: 
        draw.text((x, curr_y), f"{label}: {t} {h}", font=text_font, fill=0)
        curr_y += 14
    
    if is_tide_area and data:
        draw.text((x, curr_y + 2), f"Updated: {data.get('last_tide_time','')}", font=text_font, fill=0)

def draw_flow_block(draw, y, data, section_font, text_font):
    draw.text((10, y), "RIVER CONDITIONS", font=section_font, fill=0)
    curr_y = y + 16
    
    # Hacienda Bridge
    draw.text((10, curr_y), f"Hacienda: {data.get('hacienda_stage','--')}ft {data.get('hacienda_cfs','--')}cfs", font=text_font, fill=0)
    curr_y += 14
    
    # NEW: Jenner US-1 Bridge
    draw.text((10, curr_y), f"US-1 Bridge: {data.get('jenner_stage','--')}ft", font=text_font, fill=0)
    curr_y += 14
    
    # Mouth Status
    draw.text((10, curr_y), f"Mouth: {data.get('river_mouth_status','UNKNOWN')}", font=text_font, fill=0)
    curr_y += 14
    
    # River Timestamp
    draw.text((10, curr_y), f"Updated: {data.get('last_river_time','')}", font=text_font, fill=0)

def render_tide_layout(data):
    img = Image.new("1", (WIDTH, HEIGHT), 255) 
    draw = ImageDraw.Draw(img)
    header_font, section_font, text_font = load_fonts()

    # Header
    draw.rectangle((0, 0, WIDTH, 24), fill=0) 
    date_str = date.today().strftime("%b %d, %Y")
    bbox = draw.textbbox((0, 0), f"TIDES - {date_str}", font=header_font)
    draw.text(((WIDTH-(bbox[2]-bbox[0]))//2, 2), f"TIDES - {date_str}", font=header_font, fill=255)

    # Grid Layout
    draw_station_block(draw, 10, 35, "BODEGA BAY", data.get("bodega_tides", []), section_font, text_font)
    draw_station_block(draw, 210, 35, "FORT ROSS", data.get("fort_ross", []), section_font, text_font)
    
    draw.line((10, 115, WIDTH-10, 115), fill=0, width=1)
    
    draw_station_block(draw, 10, 125, "GOAT ROCK", data.get("goat_rock", []), section_font, text_font)
    draw_station_block(draw, 210, 125, "JENNER BEACH", data.get("jenner_beach", []), section_font, text_font)

    draw.line((10, 205, WIDTH-10, 205), fill=0, width=1)
    
    # Bottom Row
    draw_flow_block(draw, 215, data, section_font, text_font)
    draw_station_block(draw, 210, 215, "ESTUARY", data.get("estuary", []), section_font, text_font, data=data, is_tide_area=True)

    return img

# ---------- Main Loop ----------

def main():
    print("Initializing e-Paper...")
    epd = epd4in2_V2.EPD()
    
    last_mtime = 0
    while True:
        if os.path.exists(DATA_FILE):
            mtime = os.path.getmtime(DATA_FILE)
            if mtime > last_mtime:
                try:
                    with open(DATA_FILE, "r") as f:
                        data = json.load(f)
                    
                    print("Updating e-Paper Display...")
                    img = render_tide_layout(data)
                    
                    epd.init()
                    epd.display(epd.getbuffer(img))
                    epd.sleep() 
                    
                    last_mtime = mtime
                    print(f"Update Complete: {time.ctime()}")
                except Exception as e:
                    print(f"Error: {e}")
        
        time.sleep(60) 

if __name__ == "__main__":
    main()

