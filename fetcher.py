#!/usr/bin/env python3
import requests
import json
import time
import os
from datetime import datetime, timedelta

# Settings
DATA_FILE = "tides.json"
BASE_URL = "https://api.waterdata.usgs.gov/ogcapi/v0/collections"
HACIENDA_ID = "USGS-11467000"
JENNER_ID = "USGS-11467270"
BODEGA_STATION = "9415625" 
FORT_ROSS_STATION = "9416024"

# Standard browser headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0'
}

# Global variable to track the last date we successfully fetched tides
last_tide_fetch_date = ""

# ---------- Helpers ----------

def shift_time(timestr, delta_minutes):
    """Adjusts a time string (e.g., '3:58 AM') by +/- minutes."""
    try:
        t = datetime.strptime(timestr, "%I:%M %p")
        t += timedelta(minutes=delta_minutes)
        return t.strftime("%-I:%M %p")
    except:
        return timestr

def save_json(data):
    """Atomic save to trigger e-ink display refresh."""
    temp_file = DATA_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(temp_file, DATA_FILE)

# ---------- API Logic ----------

def get_latest_usgs_value(site_id, parameter="00065"):
    usgs_url = f"{BASE_URL}/latest-continuous/items"
    params = {
        "monitoring_location_id": site_id,
        "parameter_code": parameter,
        "f": "json"
    }
    print(f"--- Syncing USGS river measurements ({site_id}) ---")
    try:
        response = requests.get(usgs_url, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        if "features" in data and len(data["features"]) > 0:
            return data["features"][0].get("properties", {}).get("value")
    except Exception as e:
        print(f"FAILED USGS fetch for {site_id}: {e}")
    return None

def get_noaa_tides(station_id):
    noaa_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    
    params = {
        "begin_date": today.strftime("%Y%m%d"),
        "end_date": tomorrow.strftime("%Y%m%d"),
        "station": station_id,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "interval": "hilo",
        "units": "english",
        "application": "DataAPI_Sample",
        "format": "json"
    }
    print(f"--- Syncing NOAA tide predictions ({station_id}) ---")
    try:
        response = requests.get(noaa_url, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if "predictions" in data:
            today_str = today.strftime("%Y-%m-%d")
            formatted_tides = []
            for p in data["predictions"]:
                if p['t'].startswith(today_str):
                    label = "High" if p['type'] == 'H' else "Low"
                    t_obs = datetime.strptime(p['t'], "%Y-%m-%d %H:%M")
                    t_str = t_obs.strftime("%-I:%M %p")
                    height = f"{float(p['v']):.1f}ft"
                    formatted_tides.append((label, t_str, height))
            return formatted_tides
    except Exception as e:
        print(f"FAILED NOAA fetch for {station_id}: {e}")
    return None

# ---------- Main Execution Logic ----------

def fetch_cycle():
    global last_tide_fetch_date
    current_date_str = datetime.now().strftime("%Y-%m-%d")

    # Load baseline
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f: data = json.load(f)
        except: data = {}
    else: data = {}

    # --- PHASE 1: RIVER (Every Cycle - 1 Hour) ---
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Phase 1: USGS River Data")
    h_stage = get_latest_usgs_value(HACIENDA_ID, "00065")
    h_cfs = get_latest_usgs_value(HACIENDA_ID, "00060") 
    j_stage = get_latest_usgs_value(JENNER_ID, "00065")

    if h_stage is not None and j_stage is not None:
        data.update({
            "hacienda_stage": h_stage,
            "hacienda_cfs": h_cfs if h_cfs else data.get("hacienda_cfs", "--"),
            "jenner_stage": j_stage,
            "river_mouth_status": "CLOSED" if float(j_stage) >= 9.0 else "OPEN",
            "river_success": True,
            "last_river_time": datetime.now().strftime("%-I:%M %p")
        })
        save_json(data)
        print(f"++ River Success. H:{h_stage}ft, J:{j_stage}ft")
    else:
        data["river_success"] = False
        print("!! River Data Fetch Failed.")

    time.sleep(2) 

    # --- PHASE 2: TIDES (Once Per Day) ---
    if current_date_str != last_tide_fetch_date or "bodega_tides" not in data:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Phase 2: NOAA Tide Data (Daily Sync)")
        bodega = get_noaa_tides(BODEGA_STATION)
        fort_ross = get_noaa_tides(FORT_ROSS_STATION)

        if bodega and fort_ross:
            # Update base stations
            data.update({
                "bodega_tides": bodega,
                "fort_ross": fort_ross,
                "tide_success": True,
                "last_tide_time": datetime.now().strftime("%-I:%M %p")
            })

            # --- UPDATED DERIVED CALCULATIONS ---
            # Use Fort Ross + 5 mins for open coast (Goat Rock/Jenner Beach)
            # This avoids the "harbor lag" found in Bodega Bay data.
            goat_rock_derived = [(l, shift_time(t, 5), h) for l,t,h in fort_ross]
            data["goat_rock"] = goat_rock_derived
            data["jenner_beach"] = goat_rock_derived

            # Estuary still lags behind; keeping the Bodega Bay reference for the Estuary
            data["estuary"] = [(l, shift_time(t, 90 if l=="High" else 60), h) for l,t,h in bodega]
            
            save_json(data)
            
            # Print verification for the terminal
            print(f"++ Tides Updated using Fort Ross Reference for Goat Rock.")
            for label, t, h in goat_rock_derived:
                print(f"   Goat Rock {label}: {t} ({h})")
            
            last_tide_fetch_date = current_date_str
        else:
            data["tide_success"] = False
            print("!! Tide Data Fetch Failed.")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Phase 2: Tides skipped (Up to date).")

if __name__ == "__main__":
    fetch_cycle()
    while True:
        print(f"Sleeping 1 hour...")
        time.sleep(3600)
        fetch_cycle()
