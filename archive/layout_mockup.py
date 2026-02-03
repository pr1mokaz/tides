#!/usr/bin/env python3
"""Generate a mockup image using the new layout."""

import json
from display_eink import render_tide_layout

with open("tides.json", "r") as f:
    data = json.load(f)

img = render_tide_layout(data)
img.save("layout_mockup.png")
print("Saved layout_mockup.png")
