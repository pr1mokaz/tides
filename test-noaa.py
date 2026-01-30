import requests
import json
from datetime import datetime

# The exact successful URL components
STATION_ID = "9415625"
NOAA_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

def test_noaa_working_url():
    # Use the dates from your successful browser test
    # We can automate these strings later, but for the test we match your link
    params = {
        "begin_date": "20260126",
        "end_date": "20260127",
        "station": STATION_ID,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "interval": "hilo",
        "units": "english",
        "application": "DataAPI_Sample",
        "format": "json"
    }

    # Standard browser headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0'
    }

    print(f"--- Syncing NOAA via Verified Cloud Path ---")

    try:
        response = requests.get(NOAA_URL, params=params, headers=headers, timeout=15)
        
        # Check for the 403 before parsing
        if response.status_code == 403:
            print("FAILED: Still getting 403 Forbidden. The server is rejecting the script but not the browser.")
            return

        data = response.json()
        
        if "predictions" in data:
            print(f"SUCCESS: Found {len(data['predictions'])} predictions.\n")
            
            # Get current date string to filter results (YYYY-MM-DD)
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            for p in data["predictions"]:
                # Only show tides for today
                if p['t'].startswith(today_str):
                    t_type = "High" if p['type'] == "H" else "Low"
                    # Format time from "2026-01-27 04:52" to "4:52 AM"
                    t_obs = datetime.strptime(p['t'], "%Y-%m-%d %H:%M")
                    t_str = t_obs.strftime("%-I:%M %p")
                    
                    print(f"{t_type} Tide: {t_str} ({p['v']} ft)")
        else:
            print("FAILED: No predictions in JSON response.")
            print(f"Raw Response: {data}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_noaa_working_url()

