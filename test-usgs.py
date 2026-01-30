import requests
import json

# REQUIRED: Base URL must include /ogcapi/v0/
BASE_URL = "https://api.waterdata.usgs.gov/ogcapi/v0/collections"
SITE_ID = "USGS-11467000"

def run_usgs_test():
    print(f"--- Testing 2026 USGS OGC API for Site {SITE_ID} ---")
    
    # 1. Metadata Test
    meta_url = f"{BASE_URL}/monitoring-locations/items/{SITE_ID}"
    try:
        # f=json parameter is vital to prevent HTML default
        response = requests.get(meta_url, params={"f": "json"}, timeout=15)
        response.raise_for_status()
        print("SUCCESS: Metadata retrieved.")
    except Exception as e:
        print(f"FAILED (Metadata): {e}")

    # 2. Latest Data Test (Gage Height 00065)
    data_url = f"{BASE_URL}/latest-continuous/items"
    params = {
        "monitoring_location_id": SITE_ID,
        "parameter_code": "00065",
        "f": "json"
    }
    
    try:
        response = requests.get(data_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # CORRECTED 2026 JSON PATH: features[0] -> properties -> value
        if "features" in data and len(data["features"]) > 0:
            latest_feature = data["features"][0]
            props = latest_feature.get("properties", {})
            val = props.get("value")
            unit = props.get("unit_of_measure_code", "ft")
            
            if val is not None:
                print(f"SUCCESS: Latest Gage Height is {val} {unit}")
            else:
                print("FAILED: Feature found but 'value' field is missing.")
        else:
            print("FAILED: API connected but 'features' list is empty.")
            
    except Exception as e:
        print(f"FAILED (Data Parsing): {e}")

if __name__ == "__main__":
    run_usgs_test()

