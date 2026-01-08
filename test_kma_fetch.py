import urllib.request
import urllib.parse
import json
import ssl
import pandas as pd

# Config
# Open-Meteo Historical Forecast API
BASE_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
LAT = 37.46
LON = 126.44
DATE = "2024-01-01"

def fetch_model(model_name):
    print(f"--- Fetching {model_name} for {DATE} ---")
    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": DATE,
        "end_date": DATE,
        "hourly": "temperature_2m",
        "models": model_name,
        "temperature_unit": "fahrenheit"
    }
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                temps = data.get('hourly', {}).get('temperature_2m', [])
                if not temps: return None
                # Filter None
                valid = [t for t in temps if t is not None]
                if not valid: return None
                return max(valid)
    except Exception as e:
        print(f"Error fetching {model_name}: {e}")
        return None

def main():
    # 1. GFS (Global)
    gfs_max = fetch_model("gfs_seamless")
    
    # 2. KMA LDPS (Local High Res) - assuming key is 'kma_ldps'
    # Check if 'kma_ldps' is valid for historical.
    kma_max = fetch_model("kma_ldps") 
    
    # 3. KMA GDPS (Global)
    # kma_gdps_max = fetch_model("kma_gdps")
    
    print("\n--- RESULTS (Seoul 2024-01-01) ---")
    print("Observed (TWC): ~43 F")
    
    if gfs_max:
        print(f"GFS Forecast:   {gfs_max:.2f} F (Diff: {abs(43-gfs_max):.2f})")
    
    if kma_max:
        print(f"KMA LDPS Fcst:  {kma_max:.2f} F (Diff: {abs(43-kma_max):.2f})")
    else:
        print("KMA LDPS:       Fetch Failed or Not Available in Archive")
        
    # Recommendation
    if kma_max and abs(43-kma_max) < abs(43-gfs_max):
        print(">> WINNER: KMA LDPS (Local Model)")
    elif gfs_max:
        print(">> WINNER: GFS (Global Model)")

if __name__ == "__main__":
    main()
