#!/usr/bin/env python3
"""
Fetcher program for tides and river data.

Required files:
- fetcher.py
- data_validator.py
- tides.json (generated/updated by this script)

Dependencies:
- Python 3
- requests

Outputs:
- tides.json
"""
#
# module: fetcher.py
# dependencies: requests
# Includes: Retry logic, caching, and error recovery

import requests
import json
import time
import os
from datetime import datetime, timedelta
from data_validator import DataValidator
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# Settings
DATA_FILE = "tides.json"
BASE_URL = "https://api.waterdata.usgs.gov/ogcapi/v0/collections"
HACIENDA_ID = "USGS-11467000"
JENNER_ID = "USGS-11467270"
BODEGA_STATION = "9415625" 
FORT_ROSS_STATION = "9416024"
SF_WATER_LEVEL_STATION = "9414290"  # San Francisco for real-time water level (deviation tracking)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds, increases exponentially

# Timezone for interpreting USGS timestamps
DEFAULT_TZ = os.environ.get("TIDES_TZ", "America/Los_Angeles")
LOCAL_TZ = ZoneInfo(DEFAULT_TZ) if ZoneInfo else None

# Standard browser headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0'
}

# Global variable to track the last date we successfully fetched tides
last_tide_fetch_date = ""

# ---------- Helpers ----------

def retry_request(url, params=None, max_retries=MAX_RETRIES, timeout=15):
    """Make HTTP request with exponential backoff retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            print(f"  Timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                wait = RETRY_DELAY * (2 ** attempt)
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
        except requests.exceptions.ConnectionError as e:
            print(f"  Connection error: {e} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                wait = RETRY_DELAY * (2 ** attempt)
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
        except requests.exceptions.RequestException as e:
            print(f"  Request failed: {e}")
            return None
    
    print(f"  Failed after {max_retries} attempts")
    return None

def shift_time(timestr, delta_minutes):
    """Adjusts a time string (e.g., '3:58 AM') by +/- minutes."""
    try:
        t = datetime.strptime(timestr, "%I:%M %p")
        t += timedelta(minutes=delta_minutes)
        # Cross-platform: use %I and strip leading zero for Windows compatibility
        return t.strftime("%I:%M %p").lstrip("0")
    except Exception:
        return timestr

def save_json(data):
    """Atomic save to trigger e-ink display refresh."""
    # Backup before writing
    DataValidator.ensure_backup(DATA_FILE)
    
    temp_file = DATA_FILE + ".tmp"
    try:
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=4)
        os.replace(temp_file, DATA_FILE)
        print(f"✓ Data saved successfully")
    except Exception as e:
        print(f"✗ Failed to save data: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)

# ---------- API Logic ----------

def get_latest_usgs_value(site_id, parameter="00065"):
    usgs_url = f"{BASE_URL}/latest-continuous/items"
    params = {
        "monitoring_location_id": site_id,
        "parameter_code": parameter,
        "f": "json"
    }
    print(f"--- Syncing USGS river measurements ({site_id}) ---")
    response = retry_request(usgs_url, params=params)
    if response is None:
        print(f"✗ USGS fetch failed for {site_id}")
        return None
    
    try:
        data = response.json()
        if "features" in data and len(data["features"]) > 0:
            return data["features"][0].get("properties", {}).get("value")
    except Exception as e:
        print(f"✗ USGS parse error: {e}")
    return None

def get_usgs_daily_data(site_id, parameter="00065", days_back=1):
    """Fetch USGS daily values for a site over the past days_back days.
    Returns a list of (datetime, value) tuples.
    """
    usgs_url = f"{BASE_URL}/USGS-daily-values/items"
    params = {
        "monitoring_location_id": site_id,
        "parameter_code": parameter,
        "f": "json"
    }
    print(f"--- Fetching USGS daily data ({site_id}) ---")
    try:
        response = requests.get(usgs_url, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        if "features" in data and len(data["features"]) > 0:
            results = []
            for feature in data["features"]:
                props = feature.get("properties", {})
                dt_str = props.get("dateTime")
                value = props.get("value")
                if dt_str and value is not None:
                    try:
                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                        results.append((dt, float(value)))
                    except:
                        pass
            return results
    except Exception as e:
        print(f"FAILED USGS daily data fetch for {site_id}: {e}")
    return []

def get_usgs_iv_history(site_id, parameter="00065", period="P2D"):
    """Fetch USGS 15-min (iv) history for the last period (e.g., P2D).
    Returns dict of date_key -> list of {time, minutes, stage}.
    """
    url = "https://waterservices.usgs.gov/nwis/iv/"
    params = {
        "format": "json",
        "sites": site_id.replace("USGS-", ""),
        "parameterCd": parameter,
        "period": period
    }
    print(f"--- Fetching USGS IV history ({site_id}, {period}) ---")
    response = retry_request(url, params=params, timeout=20)
    if response is None:
        print(f"✗ USGS IV history fetch failed for {site_id}")
        return {}

    try:
        data = response.json()
        time_series = data.get("value", {}).get("timeSeries", [])
        if not time_series:
            return {}

        values = time_series[0].get("values", [])
        if not values:
            return {}

        history = {}
        for entry in values[0].get("value", []):
            dt_str = entry.get("dateTime")
            val = entry.get("value")
            if not dt_str or val in (None, ""):
                continue
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                if LOCAL_TZ:
                    dt = dt.astimezone(LOCAL_TZ)
                else:
                    dt = dt.astimezone()
                date_key = dt.strftime("%Y-%m-%d")
                minutes = dt.hour * 60 + dt.minute
                time_str = dt.strftime("%I:%M %p").lstrip("0")
                history.setdefault(date_key, []).append({
                    "time": time_str,
                    "minutes": minutes,
                    "stage": float(val)
                })
            except Exception:
                continue

        # Sort and de-dup per day by minutes
        for date_key, items in history.items():
            dedup = {}
            for item in items:
                dedup[item["minutes"]] = item
            history[date_key] = [dedup[m] for m in sorted(dedup.keys())]

        return history
    except Exception as e:
        print(f"FAILED USGS IV history parse for {site_id}: {e}")
        return {}

def interpolate_predicted_level(hour_minute, predictions_for_today):
    """Simple linear interpolation between two tide points.
    hour_minute: e.g., "14:30"
    predictions_for_today: [(label, time_str, height_str), ...]
    Returns predicted level as float, or None if unable to interpolate.
    """
    try:
        target_h, target_m = map(int, hour_minute.split(":"))
        target_mins = target_h * 60 + target_m
        
        # Parse times and heights from predictions
        events = []
        for label, time_str, height_str in predictions_for_today:
            h_str = height_str.replace("ft", "").strip()
            h_val = float(h_str)
            # Parse time (e.g., "2:30 PM" or "14:30")
            try:
                if "AM" in time_str or "PM" in time_str:
                    dt = datetime.strptime(time_str, "%I:%M %p")
                else:
                    dt = datetime.strptime(time_str, "%H:%M")
                t_mins = dt.hour * 60 + dt.minute
                events.append((t_mins, h_val))
            except:
                continue
        
        if not events or len(events) < 2:
            return None
        
        events.sort()
        
        # Find bracketing events
        for i in range(len(events) - 1):
            t1, h1 = events[i]
            t2, h2 = events[i + 1]
            if t1 <= target_mins <= t2:
                # Linear interpolation
                frac = (target_mins - t1) / (t2 - t1) if t2 != t1 else 0
                return h1 + frac * (h2 - h1)
        
        # Outside bracket: use nearest
        return events[0][1] if target_mins < events[0][0] else events[-1][1]
    except Exception as e:
        print(f"Failed to interpolate predicted level: {e}")
        return None

def get_noaa_water_level(station_id):
    """Fetch latest observed water level from NOAA.
    Returns (timestamp_str, observed_level_ft) or (None, None) on failure.
    """
    noaa_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    now = datetime.now()
    # Format: YYYYMMDD (daily range)
    begin = (now - timedelta(days=1)).strftime("%Y%m%d")
    end = now.strftime("%Y%m%d")
    
    params = {
        "station": station_id,
        "begin_date": begin,
        "end_date": end,
        "product": "water_level",
        "application": "NOS.COOPS.TAC.WL",  # Critical: required by NOAA API
        "datum": "MLLW",
        "time_zone": "GMT",
        "units": "english",
        "format": "json"
    }
    print(f"--- Fetching observed water level ({station_id}) ---")
    try:
        response = requests.get(noaa_url, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            latest = data["data"][-1]  # Most recent
            t_str = latest.get("t")
            level = float(latest.get("v", 0.0))
            return t_str, level
    except Exception as e:
        print(f"FAILED water level fetch for {station_id}: {e}")
    return None, None

def get_noaa_tides_multiday(station_id, days_forward=14, days_back=1):
    """Fetch NOAA tide predictions for station_id over the past days_back and next days_forward days.
    Returns a dict {"YYYY-MM-DD": [(label, time_str, height), ...], ...}
    """
    noaa_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    today = datetime.now()
    begin_date = today - timedelta(days=days_back)
    end_date = today + timedelta(days=days_forward)
    
    params = {
        "begin_date": begin_date.strftime("%Y%m%d"),
        "end_date": end_date.strftime("%Y%m%d"),
        "station": station_id,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "interval": "hilo",
        "units": "english",
        "application": "DataAPI_Sample",
        "format": "json"
    }
    print(f"--- Syncing NOAA tide predictions ({station_id}) for past {days_back} and next {days_forward} days ---")
    result = {}
    try:
        response = requests.get(noaa_url, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()

        if "predictions" in data:
            # Parse predictions, group by date
            preds_by_date = {}
            for p in data["predictions"]:
                try:
                    p_dt = datetime.strptime(p['t'], "%Y-%m-%d %H:%M")
                    date_key = p_dt.strftime("%Y-%m-%d")
                    if date_key not in preds_by_date:
                        preds_by_date[date_key] = []
                    preds_by_date[date_key].append({
                        'dt': p_dt,
                        'type': p.get('type'),
                        'v': float(p.get('v', 0.0))
                    })
                except Exception:
                    continue

            # For each date, extract all highs and lows and format
            for date_key in sorted(preds_by_date.keys()):
                preds = preds_by_date[date_key]
                highs = [p for p in preds if p['type'] == 'H']
                lows = [p for p in preds if p['type'] == 'L']
                
                # Sort chronologically and combine
                highs = sorted(highs, key=lambda x: x['dt'])
                lows = sorted(lows, key=lambda x: x['dt'])
                combined = sorted(highs + lows, key=lambda x: x['dt'])

                formatted_tides = []
                for p in combined:
                    label = 'High' if p['type'] == 'H' else 'Low'
                    # Cross-platform: use %I and strip leading zero for Windows compatibility
                    t_str = p['dt'].strftime("%I:%M %p").lstrip("0")
                    height = f"{p['v']:.1f}ft"
                    formatted_tides.append((label, t_str, height))

                result[date_key] = formatted_tides
    except Exception as e:
        print(f"FAILED NOAA fetch for {station_id}: {e}")
    return result

# ---------- Main Execution Logic ----------

def fetch_cycle():
    global last_tide_fetch_date
    current_date_str = datetime.now().strftime("%Y-%m-%d")

    # Load baseline with validation
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
            # Validate structure
            issues, msg, is_usable = DataValidator.validate_tides_data(data)
            if not is_usable:
                print(f"⚠ Data validation warnings: {msg}")
                if not issues:  # Still use it if usable
                    pass
        except json.JSONDecodeError as e:
            print(f"✗ JSON corruption detected: {e}, starting fresh")
            data = {}
        except Exception as e:
            print(f"✗ Failed to load {DATA_FILE}: {e}")
            data = {}
    else:
        print(f"ℹ Creating new {DATA_FILE}")
        DataValidator.create_template_if_missing(DATA_FILE)
        data = {}

    # Ensure data_sources tracking exists
    if "data_sources" not in data:
        data["data_sources"] = {}

    # --- PHASE 1: RIVER + OBSERVED WATER LEVEL (Every Cycle - 1 Hour) ---
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Phase 1: USGS River Data + NOAA Water Level")
    h_stage = get_latest_usgs_value(HACIENDA_ID, "00065")
    h_cfs = get_latest_usgs_value(HACIENDA_ID, "00060") 
    j_stage = get_latest_usgs_value(JENNER_ID, "00065")

    # Collect Jenner water stage measurements (prefer 15-min history for accuracy)
    if "jenner_stage_history" not in data:
        data["jenner_stage_history"] = {}

    # Update from USGS IV history (last 2 days) to match website peaks
    iv_history = get_usgs_iv_history(JENNER_ID, "00065", period="P2D")
    if iv_history:
        data["jenner_stage_history"].update(iv_history)
        data["data_sources"]["jenner_stage_updated"] = datetime.now().isoformat()
    elif j_stage is not None:
        # Fallback: append current reading if IV history unavailable
        current_time = datetime.now().strftime("%I:%M %p").lstrip("0")
        current_mins = datetime.now().hour * 60 + datetime.now().minute
        day_list = data["jenner_stage_history"].setdefault(current_date_str, [])
        # De-dup by minute
        day_list = [m for m in day_list if m.get("minutes") != current_mins]
        day_list.append({
            "time": current_time,
            "minutes": current_mins,
            "stage": float(j_stage)
        })
        data["jenner_stage_history"][current_date_str] = sorted(day_list, key=lambda m: m.get("minutes", 0))
        data["data_sources"]["jenner_stage_updated"] = datetime.now().isoformat()

    # Keep only last 3 days of stage history
    for date_key in list(data["jenner_stage_history"].keys()):
        try:
            dt_key = datetime.strptime(date_key, "%Y-%m-%d")
            if (datetime.now() - dt_key).days > 2:
                del data["jenner_stage_history"][date_key]
        except Exception:
            continue

    if h_stage is not None and j_stage is not None:
        data.update({
            "hacienda_stage": h_stage,
            "hacienda_cfs": h_cfs if h_cfs else data.get("hacienda_cfs", "--"),
            "jenner_stage": j_stage,
            "river_mouth_status": "CLOSED" if float(j_stage) >= 9.0 else "OPEN",
            "river_success": True,
            "last_river_time": datetime.now().strftime("%I:%M %p").lstrip("0")
        })
        save_json(data)
        print(f"++ River Success. H:{h_stage}ft, J:{j_stage}ft")
    else:
        data["river_success"] = False
        print("!! River Data Fetch Failed.")

    # Fetch observed water level for deviation tracking (San Francisco reference)
    # Note: SF is ~1.5 hrs away but has reliable real-time water level data
    time.sleep(1)
    water_ts, observed_level = get_noaa_water_level(SF_WATER_LEVEL_STATION)
    if water_ts and observed_level is not None:
        # Interpolate predicted level at this time
        current_date_key = datetime.now().strftime("%Y-%m-%d")
        today_preds = data.get("bodega_tides", {}).get(current_date_key, [])
        obs_time = datetime.strptime(water_ts, "%Y-%m-%d %H:%M")
        time_str = obs_time.strftime("%H:%M")
        predicted_level = interpolate_predicted_level(time_str, today_preds)
        
        if predicted_level is not None:
            deviation = observed_level - predicted_level
            # Store deviation with timestamp
            if "deviation_samples" not in data:
                data["deviation_samples"] = []
            data["deviation_samples"].append({
                "timestamp": water_ts,
                "observed": round(observed_level, 2),
                "predicted": round(predicted_level, 2),
                "deviation": round(deviation, 2)
            })
            # Keep only last 48 samples (2 days at 1/hour)
            data["deviation_samples"] = data["deviation_samples"][-48:]
            # Store latest deviation
            data["latest_deviation"] = round(deviation, 2)
            data["latest_water_time"] = time_str
            save_json(data)
            print(f"++ Water Level: obs={observed_level:.2f}ft, pred={predicted_level:.2f}ft, dev={deviation:.2f}ft")
        else:
            print(f"!! Could not interpolate predicted level for deviation calculation")
    else:
        print("!! Water Level Fetch Failed (station may not have real-time data).")

    time.sleep(2) 

    # --- PHASE 2: TIDES (Once Per Day, 2-week cache) ---
    if current_date_str != last_tide_fetch_date or "bodega_tides" not in data:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Phase 2: NOAA Tide Data (2-Week Sync)")
        bodega_dict = get_noaa_tides_multiday(BODEGA_STATION, days_forward=14)
        fort_ross_dict = get_noaa_tides_multiday(FORT_ROSS_STATION, days_forward=14)

        if bodega_dict and fort_ross_dict:
            # Update base stations (multi-day dicts)
            data.update({
                "bodega_tides": bodega_dict,
                "fort_ross": fort_ross_dict,
                "tide_success": True,
                "last_tide_time": datetime.now().strftime("%I:%M %p").lstrip("0")
            })

            # --- PRE-COMPUTE DERIVED STATIONS FOR ALL DAYS ---
            # Use Fort Ross + 5 mins for open coast (Goat Rock/Jenner Beach)
            # This avoids the "harbor lag" found in Bodega Bay data.
            goat_rock_dict = {}
            jenner_beach_dict = {}
            for date_key, tides in fort_ross_dict.items():
                goat_rock_dict[date_key] = [(l, shift_time(t, 5), h) for l,t,h in tides]
                jenner_beach_dict[date_key] = [(l, shift_time(t, 5), h) for l,t,h in tides]
            data["goat_rock"] = goat_rock_dict
            data["jenner_beach"] = jenner_beach_dict

            # Estuary lags Bodega Bay
            estuary_dict = {}
            for date_key, tides in bodega_dict.items():
                estuary_dict[date_key] = [(l, shift_time(t, 90 if l=="High" else 60), h) for l,t,h in tides]
            data["estuary"] = estuary_dict
            
            save_json(data)
            
            # Print verification for today's forecast
            print(f"++ 2-Week Tides Cached. Today's Goat Rock forecast:")
            if current_date_str in goat_rock_dict:
                for label, t, h in goat_rock_dict[current_date_str]:
                    print(f"   {label}: {t} ({h})")
            
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
