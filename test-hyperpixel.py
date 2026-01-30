import os
import platform
from PIL import Image, ImageDraw, ImageFont

FB_PATH = "/dev/fb0"

# Get framebuffer resolution
def get_fb_resolution():
    with open("/sys/class/graphics/fb0/virtual_size", "r") as f:
        w, h = f.read().strip().split(",")
        return int(w), int(h)

width, height = get_fb_resolution()

# Create an RGB test image
img = Image.new("RGB", (width, height), "black")
draw = ImageDraw.Draw(img)

# Draw colored bars
bar_height = height // 4
colors = ["red", "green", "blue", "white"]

for i, color in enumerate(colors):
    draw.rectangle(
        [0, i * bar_height, width, (i + 1) * bar_height],
        fill=color
    )

# Add identification text
font = ImageFont.load_default()
text = f"HyperPixel 4.0 Test\nModel: {platform.machine()}\nOS: {platform.platform()}"
draw.text((10, 10), text, font=font, fill="black")

# Write to framebuffer
with open(FB_PATH, "wb") as fb:
    fb.write(img.tobytes())

print("HyperPixel test image displayed.")
