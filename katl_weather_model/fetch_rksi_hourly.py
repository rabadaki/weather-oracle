import urllib.request
import urllib.parse
import pandas as pd
import json
import time
import ssl
import numpy as np

# Config
# Open-Meteo starts 2016-01-01 for JMA
START_YEAR = 2016 
END_YEAR = 2025
LOCATION_LAT = 37.46
LOCATION_LON = 126.44
OM_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
TWC_URL_BASE = "https://api.weather.com/v1/location/RKSI:9:KR/observations/historical.json"
TWC_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
OUTPUT_FILE = "rksi_sophisticated_data.csv"

def fetch_url(url, params=None):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=30) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
    except Exception as e:
        print(f"Fetch Error: {e} for {url}")
        return None

def fetch_jma_hourly_features():
    print(f"--- Fetching JMA GSM Hourly Features ({START_YEAR}-{END_YEAR}) ---")
    
    # We fetch in chunks of years to be safe, or all at once?
    # Open-Meteo can handle ~10 years usually. Let's try one go.
    params = {
        "latitude": LOCATION_LAT,
        "longitude": LOCATION_LON,
        "start_date": f"{START_YEAR}-01-01",
        "end_date": f"{END_YEAR}-12-31",
        "hourly": "temperature_2m",
        "models": "jma_gsm",
        "temperature_unit": "fahrenheit"
    }
    
    data = fetch_url(OM_URL, params)
    if not data: return None
    
    # Process into [Date, Hour_0, Hour_1, ... Hour_23]
    hourly = data['hourly']
    times = pd.to_datetime(hourly['time']) # UTC usually
    temps = hourly['temperature_2m']
    
    df = pd.DataFrame({'time': times, 'temp': temps})
    
    # Convert to Seoul Time
    df = df.set_index('time')
    # Use 'UTC' localizing if naive
    if df.index.tz is None:
        df = df.tz_localize('UTC')
    df = df.tz_convert('Asia/Seoul')
    
    # We want to pivot: Index=Date, Columns=Hours (0-23)
    df['Date'] = df.index.date
    df['Hour'] = df.index.hour
    
    # Pivot
    # Result: Index=Date, Cols=0,1,2...23
    pivot = df.pivot(index='Date', columns='Hour', values='temp')
    
    # Rename cols to JMA_00, JMA_01...
    pivot.columns = [f"JMA_{h:02d}" for h in pivot.columns]
    
    # Also calculate a JMA_Max (Daily Max) for baseline comparison
    pivot['JMA_Max_Daily'] = pivot.max(axis=1)
    
    print(f"JMA Hourly Processed: {len(pivot)} days")
    return pivot

def fetch_twc_daily_targets():
    print(f"--- Fetching TWC Actuals ({START_YEAR}-{END_YEAR}) ---")
    
    all_obs = []
    dates = pd.date_range(start=f"{START_YEAR}-01-01", end=f"{END_YEAR}-12-31", freq='MS')
    total = len(dates)
    
    for i, d in enumerate(dates):
        start_str = d.strftime("%Y%m%d")
        next_month = d + pd.offsets.MonthBegin(1)
        end_d = next_month - pd.Timedelta(days=1)
        end_str = end_d.strftime("%Y%m%d")
        
        url = f"{TWC_URL_BASE}?units=e&startDate={start_str}&endDate={end_str}&apiKey={TWC_KEY}"
        
        data = fetch_url(url)
        if data:
            for o in data.get('observations', []):
                if o.get('temp') is not None:
                    # Valid Time GMT -> Seoul
                    ts = o.get('valid_time_gmt')
                    dt = pd.to_datetime(ts, unit='s', utc=True).tz_convert('Asia/Seoul')
                    all_obs.append({'Date': dt.date(), 'Temp': o['temp']})
        
        if i % 12 == 0:
            print(f"TWC Progress: {d.year} ({i}/{total})")
        time.sleep(0.1) # Polite
        
    df = pd.DataFrame(all_obs)
    if df.empty: return None
    
    # Group by Date -> Max Temp
    daily_max = df.groupby('Date')['Temp'].max()
    daily_max.name = "Target_MaxTemp"
    
    print(f"TWC Actuals Processed: {len(daily_max)} days")
    return daily_max

def main():
    # 1. Fetch Features
    features = fetch_jma_hourly_features()
    
    # 2. Fetch Targets
    targets = fetch_twc_daily_targets()
    
    if features is None or targets is None:
        print("Failed to fetch data.")
        return
    
    # 3. Merge
    features.index = pd.to_datetime(features.index)
    targets.index = pd.to_datetime(targets.index)
    
    merged = pd.concat([features, targets], axis=1, join='inner')
    
    print(f"Merged Dataset: {len(merged)} days.")
    merged.to_csv(OUTPUT_FILE)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
