#!/usr/bin/env python3
import requests
import json
import time
import os
from datetime import datetime, timedelta

# Settings
DATA_FILE = "tides.json"
HACIENDA_ID = "11467000"
JENNER_ID = "11467270"
BODEGA_STATION = "9415625" 
FORT_ROSS_STATION = "9416024"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}

session = requests.Session()
session.headers.update(HEADERS)

# ---------- Helpers ----------

def determine_mouth_status(jenner_stage):
    """Calculates status based on Jenner gage height threshold (9.0 ft)."""
    try:
        stage = float(jenner_stage)
        # Mouth is considered closed if water level stays above 9ft
        if stage >= 9.0:
            return "CLOSED"
        return "OPEN"
    except (ValueError, TypeError):
        return "UNKNOWN"

def shift_time(timestr, delta_minutes):
    try:
        t = datetime.strptime(timestr, "%I:%M %p")
        t += timedelta(minutes=delta_minutes)
        return t.strftime("%-I:%M %p")
    except:
        return timestr

def safe_get(url, params=None):
    try:
        response = session.get(url, params=params, timeout=15)
        if response.status_code == 200 and response.text.strip():
            return response.json()
    except:
        pass
    return None

# ---------- API Logic ----------

def get_noaa_tides(station_id):
    url = "https://api.tidesandcurrents.noaa.gov"
    params = {
        "date": "today", "station": station_id, "product": "predictions",
        "datum": "MLLW", "time_zone": "lst_ldt", "interval": "hilo",
        "units": "english", "format": "json"
    }
    data = safe_get(url, params=params)
    if not data or "predictions" not in data:
        return None
    return [
        ("High" if p['type'] == 'H' else "Low", 
         datetime.strptime(p['t'], "%Y-%m-%d %H:%M").strftime("%-I:%M %p"), 
         f"{float(p['v']):.1f} ft") 
        for p in data["predictions"]
    ]

def get_usgs_data(site_id, parameter):
    url = "https://waterservices.usgs.gov"
    params = {"format": "json", "sites": site_id, "parameterCd": parameter, "siteStatus": "all"}
    data = safe_get(url, params=params)
    try:
        # USGS Path: value -> timeSeries -> values -> value -> value
        return data['value']['timeSeries'][0]['values'][0]['value'][0]['value']
    except:
        return None

# ---------- Main Logic ----------

def fetch_and_save():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching...")
    
    # 1. Fetch Tides
    bodega = get_noaa_tides(BODEGA_STATION)
    fort_ross = get_noaa_tides(FORT_ROSS_STATION)
    tide_success = bodega is not None
    
    # 2. Fetch River
    h_stage = get_usgs_data(HACIENDA_ID, "00065")
    h_cfs = get_usgs_data(HACIENDA_ID, "00060")
    j_stage = get_usgs_data(JENNER_ID, "00065")
    river_success = h_stage is not None

    if not tide_success and not river_success:
        print("!! Both Tide and River APIs failed. Skipping update.")
        return

    # Load old data for persistence
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            old_data = json.load(f)
    else:
        old_data = {}

    # Handle Tide Data
    if tide_success:
        goat_rock = [(l, shift_time(t, -45), h) if l == "High" else (l, shift_time(t, -15), h) for l, t, h in bodega]
        estuary = [(l, shift_time(t, 90), h) if l == "High" else (l, shift_time(t, 60), h) for l, t, h in bodega]
        last_tide_time = datetime.now().strftime("%-I:%M %p")
    else:
        bodega = old_data.get("bodega_tides", [])
        fort_ross = old_data.get("fort_ross", [])
        goat_rock = old_data.get("goat_rock", [])
        estuary = old_data.get("estuary", [])
        last_tide_time = old_data.get("last_tide_time", "Unknown")

    # Determine mouth status using the j_stage we just fetched
    mouth_status = determine_mouth_status(j_stage)

    full_data = {
        "bodega_tides": bodega,
        "fort_ross": fort_ross if fort_ross else [],
        "goat_rock": goat_rock,
        "jenner_beach": goat_rock,
        "estuary": estuary,
        "hacienda_stage": h_stage if river_success else old_data.get("hacienda_stage", "N/A"),
        "hacienda_cfs": h_cfs if h_cfs else old_data.get("hacienda_cfs", "N/A"),
        "jenner_stage": j_stage if j_stage else old_data.get("jenner_stage", "N/A"),
        "river_mouth_status": mouth_status, 
        "tide_success": tide_success,
        "river_success": river_success,
        "last_tide_time": last_tide_time,
        "last_river_time": datetime.now().strftime("%-I:%M %p") if river_success else old_data.get("last_river_time", "Unknown")
    }

    temp_file = DATA_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(full_data, f, indent=4)
    os.replace(temp_file, DATA_FILE)
    print(f"++ Sync'd. Mouth: {mouth_status} / Hacienda: {h_stage}ft")

if __name__ == "__main__":
    fetch_and_save()
    while True:
        try:
            time.sleep(900)
            fetch_and_save()
        except KeyboardInterrupt:
            break
