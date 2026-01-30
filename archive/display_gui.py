#!/usr/bin/env python3
import mmap
import json
import os
import time
from datetime import date, datetime
from PIL import Image, ImageDraw, ImageFont

# Settings
FB_PATH = "/dev/fb0"
WIDTH = 800
HEIGHT = 480
DATA_FILE = "tides.json"

# ---------- Drawing Helpers ----------

def clear_fb():
    fb_size = WIDTH * HEIGHT * 4
    if not os.path.exists(FB_PATH): return
    try:
        with open(FB_PATH, "r+b") as f:
            mm = mmap.mmap(f.fileno(), fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE)
            mm.seek(0)
            mm.write(b"\x00" * fb_size)
            mm.close()
    except Exception as e:
        print(f"FB Clear Error: {e}")

def create_canvas():
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    return img, draw

def load_fonts():
    try:
        # Standard Raspberry Pi OS font paths
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        section_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        header_font = section_font = text_font = ImageFont.load_default()
    return header_font, section_font, text_font

def draw_centered(draw, text, y, font, color=(255,255,255,255)):
    # Using modern textbbox (replaces deprecated textsize)
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    x = (WIDTH - w) // 2
    draw.text((x, y), text, font=font, fill=color)

def draw_divider(draw, y):
    draw.line((0, y, WIDTH, y), fill=(200,200,200,255), width=1)

def draw_station_block(draw, x, y, title, tides, section_font, text_font, data=None, is_tide_area=False):
    draw.text((x, y), title, font=section_font, fill=(255,255,255,255))
    curr_y = y + 28
    for label, t, h in tides:
        draw.text((x, curr_y), f"{label}: {t}   {h}", font=text_font, fill=(220,220,220,255))
        curr_y += 22
    
    # The second "Last Measured" specifically for Tides
    if is_tide_area and data:
        tide_color = (200,200,200,255) if data.get("tide_success") else (255, 60, 60, 255)
        draw.text((x, curr_y + 4), f"Last Measured: {data.get('last_tide_time')}", font=text_font, fill=tide_color)

def draw_flow_block(draw, y, data, section_font, text_font):
    draw.text((10, y), "RUSSIAN RIVER CONDITIONS", font=section_font, fill=(255,255,255,255))
    curr_y = y + 28
    
    # Draw River Stats
    draw.text((10, curr_y), f"Hacienda Bridge:   {data.get('hacienda_stage', 'N/A')} ft   {data.get('hacienda_cfs', 'N/A')} cfs", font=text_font, fill=(220,220,220,255))
    curr_y += 22
    draw.text((10, curr_y), f"US-1 Bridge:       {data.get('jenner_stage', 'N/A')} ft", font=text_font, fill=(220,220,220,255))
    curr_y += 22
    
    # River Mouth Status
    label = "River Mouth:"
    status = data.get('river_mouth_status', 'UNKNOWN')
    draw.text((10, curr_y), label, font=text_font, fill=(255,255,255,255))
    
    # Use textlength to offset the green status text correctly
    label_w = draw.textlength(label, font=text_font)
    draw.text((10 + label_w + 8, curr_y), status, font=text_font, fill=(180,255,180,255))
    
    # River Timestamp (turns RED on error)
    curr_y += 22
    river_color = (200,200,200,255) if data.get("river_success") else (255, 60, 60, 255)
    draw.text((10, curr_y), f"Last measured:     {data.get('last_river_time')}", font=text_font, fill=river_color)

# ---------- Layout & Framebuffer ----------

def image_to_fb(img):
    rgba = img.tobytes()
    bgra = bytearray(len(rgba))
    # Convert RGBA to BGRA for Linux Framebuffer (standard for Pi)
    for i in range(0, len(rgba), 4):
        r, g, b, a = rgba[i:i+4]
        bgra[i+0], bgra[i+1], bgra[i+2], bgra[i+3] = b, g, r, a
    
    try:
        with open(FB_PATH, "r+b") as f:
            mm = mmap.mmap(f.fileno(), WIDTH * HEIGHT * 4, mmap.MAP_SHARED, mmap.PROT_WRITE)
            mm.write(bgra)
            mm.close()
    except Exception as e:
        print(f"Framebuffer Write Error: {e}")

def render_tide_layout(data):
    img, draw = create_canvas()
    header_font, section_font, text_font = load_fonts()

    # Blue Header Bar
    draw.rectangle((0, 0, WIDTH, 40), fill=(0,40,80,255))
    date_str = date.today().strftime("%A, %B %d, %Y")
    draw_centered(draw, f"TIDES — {date_str}", 8, header_font)
    draw_divider(draw, 45)

    # Station Blocks
    draw_station_block(draw, 20, 55, "BODEGA BAY", data.get("bodega_tides", []), section_font, text_font)
    draw_station_block(draw, 420, 55, "FORT ROSS", data.get("fort_ross", []), section_font, text_font)
    
    draw_divider(draw, 178)
    draw_station_block(draw, 20, 183, "GOAT ROCK BEACH", data.get("goat_rock", []), section_font, text_font)
    draw_station_block(draw, 420, 183, "JENNER BEACH", data.get("jenner_beach", []), section_font, text_font)

    draw_divider(draw, 300)
    
    # Bottom Row
    draw_flow_block(draw, 310, data, section_font, text_font)
    
    # Russian River Estuary gets the second timestamp
    draw_station_block(draw, 420, 310, "RUSSIAN RIVER ESTUARY", 
                       data.get("estuary", []), section_font, text_font, 
                       data=data, is_tide_area=True)

    return img

# ---------- Main Loop ----------

def main():
    print("Starting Display Controller...")
    last_mtime = 0
    while True:
        if os.path.exists(DATA_FILE):
            mtime = os.path.getmtime(DATA_FILE)
            if mtime > last_mtime:
                try:
                    with open(DATA_FILE, "r") as f:
                        data = json.load(f)
                    img = render_tide_layout(data)
                    image_to_fb(img)
                    last_mtime = mtime
                    print(f"Screen Updated: {time.ctime()}")
                except Exception as e:
                    print(f"Display update error: {e}")
        time.sleep(2)

if __name__ == "__main__":
    main()
