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
    'User-Agent': 'TideFetcher/2.0 (Raspberry Pi Zero W; USGS-NOAA-Migration)'
}

session = requests.Session()
session.headers.update(HEADERS)

def determine_mouth_status(jenner_stage):
    try:
        if jenner_stage is None: return "UNKNOWN"
        return "CLOSED" if float(jenner_stage) >= 9.0 else "OPEN"
    except (ValueError, TypeError): return "UNKNOWN"

def shift_time(timestr, delta_minutes):
    try:
        t = datetime.strptime(timestr, "%I:%M %p")
        t += timedelta(minutes=delta_minutes)
        return t.strftime("%-I:%M %p")
    except: return timestr

def safe_get(url, params=None):
    try:
        # 30s timeout is critical for the Pi Zero's slower CPU during SSL handshakes
        response = session.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        print(f"!! HTTP Error {response.status_code} for {url}")
    except Exception as e:
        print(f"!! Connection error: {e}")
    return None

def get_noaa_tides(station_id):
    # Use the full API production path for cloud-migration compatibility
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
    # USGS has modernized their JSON nesting; old code often breaks here
    url = "
"
    params = {"format": "json", "sites": site_id, "parameterCd": parameter, "siteStatus": "all"}
    data = safe_get(url, params=params)
    try:
        # NEW JSON PATH: value -> timeSeries[0] -> values[0] -> value[0] -> value
        # Note: If the gauge is down, this path may exist but value[0] will be empty.
        series = data['value']['timeSeries'][0]['values'][0]['value']
        return series[0]['value'] if series else None
    except (KeyError, IndexError, TypeError):
        return None

def fetch_and_save():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching...")
    
    bodega = get_noaa_tides(BODEGA_STATION)
    fort_ross = get_noaa_tides(FORT_ROSS_STATION)
    tide_success = bodega is not None
    
    h_stage = get_usgs_data(HACIENDA_ID, "00065")
    h_cfs = get_usgs_data(HACIENDA_ID, "00060")
    j_stage = get_usgs_data(JENNER_ID, "00065")
    river_success = j_stage is not None # Jenner stage is crucial for mouth status

    if not tide_success and not river_success:
        print("!! Data update failed. Keeping old data.")
        return

    # Load persistent cache
    old_data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            old_data = json.load(f)

    if tide_success:
        goat_rock = [(l, shift_time(t, -45), h) if l == "High" else (l, shift_time(t, -15), h) for l, t, h in bodega]
        estuary = [(l, shift_time(t, 90), h) if l == "High" else (l, shift_time(t, 60), h) for l, t, h in bodega]
        last_tide_time = datetime.now().strftime("%-I:%M %p")
    else:
        bodega, fort_ross, goat_rock, estuary = [old_data.get(k, []) for k in ["bodega_tides", "fort_ross", "goat_rock", "estuary"]]
        last_tide_time = old_data.get("last_tide_time", "Unknown")

    mouth_status = determine_mouth_status(j_stage if river_success else old_data.get("jenner_stage"))

    full_data = {
        "bodega_tides": bodega, "fort_ross": fort_ross, "goat_rock": goat_rock,
        "jenner_beach": goat_rock, "estuary": estuary,
        "hacienda_stage": h_stage if river_success else old_data.get("hacienda_stage", "N/A"),
        "hacienda_cfs": h_cfs if river_success else old_data.get("hacienda_cfs", "N/A"),
        "jenner_stage": j_stage if river_success else old_data.get("jenner_stage", "N/A"),
        "river_mouth_status": mouth_status, 
        "tide_success": tide_success, "river_success": river_success,
        "last_tide_time": last_tide_time,
        "last_river_time": datetime.now().strftime("%-I:%M %p") if river_success else old_data.get("last_river_time", "Unknown")
    }

    with open(DATA_FILE + ".tmp", "w") as f:
        json.dump(full_data, f, indent=4)
    os.replace(DATA_FILE + ".tmp", DATA_FILE)
    print(f"++ Updated: Mouth {mouth_status}")

if __name__ == "__main__":
    fetch_and_save()
    while True:
        try:
            time.sleep(900)
            fetch_and_save()
        except KeyboardInterrupt: break

