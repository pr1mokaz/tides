import sys
import os
import time
from PIL import Image, ImageDraw

# Path setup
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'e-Paper/RaspberryPi_JetsonNano/python/lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd4in2_V2

try:
    epd = epd4in2_V2.EPD()
    epd.init()
    
    # 1. Create a blank white image
    # Note: '1' is 1-bit pixel (Black/White), 255 is White
    img = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(img)

    # 2. Draw a border around the very edge of the screen
    # This checks if we are reaching all 400x300 pixels
    draw.rectangle((0, 0, epd.width - 1, epd.height - 1), outline=0)

    # 3. Draw an "X" from corner to corner
    draw.line((0, 0, epd.width, epd.height), fill=0, width=3)
    draw.line((0, epd.height, epd.width, 0), fill=0, width=3)

    # 4. Draw some horizontal and vertical lines at set intervals
    for i in range(0, epd.width, 100):
        draw.line((i, 0, i, 50), fill=0, width=2) # Top markers
        
    # 5. Push to display
    print("Drawing lines to screen...")
    epd.display(epd.getbuffer(img))
    
    print("Success. Sleeping in 5 seconds...")
    time.sleep(5)
    epd.sleep()

except Exception as e:
    print(f"Error: {e}")


