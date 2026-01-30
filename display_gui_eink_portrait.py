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
    except:
        header_font = section_font = text_font = ImageFont.load_default()
    return header_font, section_font, text_font

def draw_station_block(draw, x, y, title, tides, section_font, text_font):
    draw.text((x, y), title, font=section_font, fill=0)
    curr_y = y + 18
    for label, t, h in tides[:3]: 
        draw.text((x, curr_y), f"{label}: {t} {h}", font=text_font, fill=0)
        curr_y += 14
    return curr_y

def draw_flow_block(draw, x, y, data, section_font, text_font):
    draw.text((x, y), "W. RUSSIAN RIVER CONDITIONS", font=section_font, fill=0)
    curr_y = y + 18
    draw.text((x, curr_y), f"Hacienda Bridge:      {data.get('hacienda_stage','--')} ft {data.get('hacienda_cfs','--')}cfs", font=text_font, fill=0)
    curr_y += 14
    draw.text((x, curr_y), f"Jenner US-1 Bridge: {data.get('jenner_stage','--')} ft", font=text_font, fill=0)
    curr_y += 14
    curr_y += 2
    draw.text((x, curr_y), f"Mouth:                       {data.get('river_mouth_status','UNKNOWN')}", font=text_font, fill=0)
    curr_y += 14

def render_tide_layout(data):
    # Create Portrait Image
    img = Image.new("1", (WIDTH, HEIGHT), 255) 
    draw = ImageDraw.Draw(img)
    header_font, section_font, text_font = load_fonts()

    # 1. Header Bar
    draw.rectangle((0, 0, WIDTH, 28), fill=0) 
    date_str = date.today().strftime("%b %d, %Y")
    bbox = draw.textbbox((0, 0), f"TIDES - {date_str}", font=header_font)
    draw.text(((WIDTH-(bbox[2]-bbox[0]))//2, 4), f"TIDES - {date_str}", font=header_font, fill=255)

    # 2. Block 1: Coastal (Bodega & Fort Ross side-by-side)
    draw_station_block(draw, 10, 35, "BODEGA BAY", data.get("bodega_tides", []), section_font, text_font)
    draw_station_block(draw, 160, 35, "FORT ROSS", data.get("fort_ross", []), section_font, text_font)
    
    # 3. Block 2: Beach & Estuary (Goat Rock & Estuary side-by-side)
    draw_station_block(draw, 10, 110, "GOAT ROCK", data.get("goat_rock", []), section_font, text_font)
    draw_station_block(draw, 160, 110, "JENNER ESTUARY", data.get("estuary", []), section_font, text_font)
    
    # Add the tide timestamp here
    draw.text((100, 180, ), f"Updated: {data.get('last_tide_time','')}", font=text_font, fill=0)

    draw.line((10, 205, WIDTH-10, 205), fill=0, width=1)
    
    # 4. Block 3: West Russian River Conditions (Full Width)
    draw_flow_block(draw, 10, 215, data, section_font, text_font)

    # Add the river timestamp here
    draw.text((100, 280), f"Updated: {data.get('last_river_time','')}", font=text_font, fill=0)

    draw.line((10, 300, WIDTH-10, 300), fill=0, width=1)

    return img

# ---------- Main Loop ----------

def main():
    print("Initializing e-Paper (Portrait)...")
    epd = epd4in2_V2.EPD()
    
    last_mtime = 0
    while True:
        if os.path.exists(DATA_FILE):
            mtime = os.path.getmtime(DATA_FILE)
            if mtime > last_mtime:
                try:
                    with open(DATA_FILE, "r") as f:
                        data = json.load(f)
                    
                    print("Updating Portrait Display...")
                    img = render_tide_layout(data)
                    
                    epd.init()
                    # We pass the 300x400 buffer; the EPD driver handles the hardware orientation
                    epd.display(epd.getbuffer(img))
                    epd.sleep() 
                    
                    last_mtime = mtime
                    print(f"Update Complete: {time.ctime()}")
                except Exception as e:
                    print(f"Error: {e}")
        
        time.sleep(60) 

if __name__ == "__main__":
    main()
