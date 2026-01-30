import sys
import os
import logging
import time

# Adjust these paths to match your directory structure
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'e-Paper/RaspberryPi_JetsonNano/python/lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd4in2_V2
from PIL import Image

logging.basicConfig(level=logging.DEBUG)

try:
    epd = epd4in2_V2.EPD()
    
    # STEP 1: Verify Resolution
    logging.info(f"Reported Width: {epd.width}")
    logging.info(f"Reported Height: {epd.height}")
    
    if epd.width != 400 or epd.height != 300:
        logging.warning("RESOLUTION MISMATCH! Expected 400x300 for Rev2.2")

    logging.info("Initializing Display...")
    epd.init()

    # STEP 2: Pure White Clear (Reset)
    logging.info("Clearing to ALL WHITE (1/2)...")
    epd.Clear() # Internal driver command to flood with 0xFF
    time.sleep(2)

    # STEP 3: Manual Solid Black Test
    # This verifies if the buffer is actually mapping to the whole screen
    logging.info("Testing SOLID BLACK (Manual Buffer)...")
    black_image = Image.new('1', (epd.width, epd.height), 0) # 0 is black
    epd.display(epd.getbuffer(black_image))
    time.sleep(5)

    # STEP 4: Final White Clear
    logging.info("Final Clear to White...")
    epd.Clear()

    logging.info("Debug Complete. Module entering sleep.")
    epd.sleep()

except Exception as e:
    logging.error(f"Debug failed: {e}")


