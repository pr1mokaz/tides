#!/usr/bin/env python3
import mmap
from datetime import date, datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

FB_PATH = "/dev/fb0"
WIDTH = 800
HEIGHT = 480

# ---------- Tide Time Helpers ----------

def shift_time(timestr, delta_minutes):
    """Shift a time like '3:58 AM' by +/- minutes."""
    t = datetime.strptime(timestr, "%I:%M %p")
    t += timedelta(minutes=delta_minutes)
    return t.strftime("%-I:%M %p")

# ---------- Base Tide Data (Bodega Bay) ----------

bodega_tides = [
    ("High", "3:58 AM", "5.8 ft"),
    ("Low",  "11:27 AM", "0.7 ft"),
    ("High", "6:08 PM", "3.4 ft"),
    ("Low",  "10:26 PM", "2.9 ft"),
]

# ---------- Derived Tide Data ----------

# Goat Rock & Jenner Beach (same offsets)
goat_rock = []
jenner_beach = []

for label, t, h in bodega_tides:
    if label == "High":
        new_t = shift_time(t, -45)   # 45 min before
    else:
        new_t = shift_time(t, -15)   # 15 min before
    goat_rock.append((label, new_t, h))
    jenner_beach.append((label, new_t, h))

# Russian River Estuary (mouth open)
estuary = []
for label, t, h in bodega_tides:
    if label == "High":
        new_t = shift_time(t, +90)   # 1.5 hours after
    else:
        new_t = shift_time(t, +60)   # 1 hour after
    estuary.append((label, new_t, h))

# ---------- Flow + Stage Placeholders (USGS later) ----------

hacienda_stage = "7.58"
hacienda_cfs = "60"
jenner_stage = "5.95"
river_mouth_status = "OPEN"
last_measured_time = "8:15am PST"

# ---------- Drawing Helpers ----------

def clear_fb():
    fb_size = WIDTH * HEIGHT * 4
    with open(FB_PATH, "r+b") as f:
        mm = mmap.mmap(f.fileno(), fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE)
        mm.seek(0)
        mm.write(b"\x00" * fb_size)
        mm.close()

def create_canvas():
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    return img, draw

def load_fonts():
    try:
        header_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        section_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        text_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        header_font = section_font = text_font = ImageFont.load_default()
    return header_font, section_font, text_font

def draw_centered(draw, text, y, font, color=(255,255,255,255)):
    w, h = draw.textsize(text, font=font)
    x = (WIDTH - w) // 2
    draw.text((x, y), text, font=font, fill=color)

def draw_divider(draw, y):
    draw.line((0, y, WIDTH, y), fill=(200,200,200,255), width=1)

def draw_station_block(draw, x, y, title, tides, section_font, text_font):
    draw.text((x, y), title, font=section_font, fill=(255,255,255,255))
    y += 28
    for label, t, h in tides:
        draw.text((x, y), f"{label}: {t}   {h}",
                  font=text_font, fill=(220,220,220,255))
        y += 22

def draw_flow_block(draw, y, section_font, text_font):
    draw.text((0, y), "RUSSIAN RIVER CONDITIONS",
              font=section_font, fill=(255,255,255,255))
    y += 28

    # Hacienda Bridge (stage + discharge)
    draw.text((10, y),
              f"Hacienda Bridge:   {hacienda_stage} ft   {hacienda_cfs} cfs",
              font=text_font, fill=(220,220,220,255))
    y += 22

    # US‑1 Bridge (stage only)
    draw.text((10, y),
              f"US-1 Bridge:       {jenner_stage} ft",
              font=text_font, fill=(220,220,220,255))
    y += 22

    # River Mouth: label white, value green
    label = "River Mouth:"
    value = f"  {river_mouth_status}"

    draw.text((10, y), label, font=text_font, fill=(255,255,255,255))
    label_width, _ = draw.textsize(label, font=text_font)

    draw.text((10 + label_width, y), value,
              font=text_font, fill=(180,255,180,255))
    y += 22

    # Timestamp
    draw.text((10, y),
              f"Last measured:     {last_measured_time}",
              font=text_font, fill=(200,200,200,255))

# ---------- Layout & Rendering ----------

def render_tide_layout():
    img, draw = create_canvas()
    header_font, section_font, text_font = load_fonts()

    # Header bar
    draw.rectangle((0, 0, WIDTH, 40), fill=(0,40,80,255))
    today = date.today()
    date_str = today.strftime("%A, %B %d, %Y")
    draw_centered(draw, f"TIDES — {date_str}", 8, header_font)

    draw_divider(draw, 45)

    left_x = 20
    right_x = 420

    # Top block: Bodega + Fort Ross
    top_y = 55
    draw_station_block(draw, left_x, top_y, "BODEGA BAY",
                       bodega_tides, section_font, text_font)
    draw_station_block(draw, right_x, top_y, "FORT ROSS",
                       bodega_tides, section_font, text_font)

    # Divider above beaches (moved up 22 px)
    draw_divider(draw, 178)

    # Middle block: Goat Rock + Jenner Beach (moved up 22 px)
    beach_y = 183
    draw_station_block(draw, left_x, beach_y, "GOAT ROCK BEACH",
                       goat_rock, section_font, text_font)
    draw_station_block(draw, right_x, beach_y, "JENNER BEACH",
                       jenner_beach, section_font, text_font)

    draw_divider(draw, 300)

    # Bottom block: Flow (left) + Estuary (right)
    flow_y = 310
    estuary_y = 310

    draw_flow_block(draw, flow_y, section_font, text_font)
    draw_station_block(draw, right_x, estuary_y,
                       "RUSSIAN RIVER ESTUARY",
                       estuary, section_font, text_font)

    return img

# ---------- Framebuffer Write ----------

def image_to_fb(img):
    if img.size != (WIDTH, HEIGHT):
        img = img.resize((WIDTH, HEIGHT))

    rgba = img.tobytes()
    bgra = bytearray(len(rgba))

    for i in range(0, len(rgba), 4):
        r, g, b, a = rgba[i:i+4]
        bgra[i+0] = b
        bgra[i+1] = g
        bgra[i+2] = r
        bgra[i+3] = a

    fb_size = WIDTH * HEIGHT * 4

    with open(FB_PATH, "r+b") as f:
        mm = mmap.mmap(f.fileno(), fb_size,
                       mmap.MAP_SHARED, mmap.PROT_WRITE | mmap.PROT_READ)
        mm.seek(0)
        mm.write(bgra[:fb_size])
        mm.close()

def main():
    clear_fb()
    img = render_tide_layout()
    image_to_fb(img)

if __name__ == "__main__":
    main()
