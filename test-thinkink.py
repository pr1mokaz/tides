import time
import board
import digitalio
from adafruit_epd.ssd1680 import Adafruit_SSD1680
from PIL import Image, ImageDraw, ImageFont

# --- Pin definitions for 2.13" ThinkInk ---
ecs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D22)
rst = digitalio.DigitalInOut(board.D27)
busy = digitalio.DigitalInOut(board.D17)

# --- Initialize display ---
display = Adafruit_SSD1680(
    250, 122,  # resolution for 2.13" B/W
    ecs, dc, sck=board.SCK, mosi=board.MOSI,
    rst=rst, busy=busy
)

display.rotation = 1  # rotate if needed

# --- Create blank image ---
image = Image.new("1", (display.width, display.height), 1)  # 1 = white
draw = ImageDraw.Draw(image)

# Load a default font
font = ImageFont.load_default()

# --- Draw test content ---
draw.text((10, 10), "ThinkInk Test OK", font=font, fill=0)
draw.text((10, 40), "Hello from Pi Zero W!", font=font, fill=0)
draw.text((10, 70), "E-Ink refresh incoming...", font=font, fill=0)

# --- Display it ---
display.image(image)
display.display()

print("Display updated successfully!")