import requests
import json

# Testing the Metadata API instead of Data API
MD_URL = "https://api.tidesandcurrents.noaa.gov"

def test_metadata_api():
    print("--- Testing NOAA Metadata API (MDAPI) ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(MD_URL, headers=headers, timeout=15)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("SUCCESS: Metadata API is reachable!")
        else:
            print(f"FAILED: {response.text}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_metadata_api()

