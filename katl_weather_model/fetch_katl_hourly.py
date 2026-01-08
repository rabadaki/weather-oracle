import urllib.request
import urllib.parse
import pandas as pd
import json
import time
import ssl
import numpy as np

# Config
START_YEAR = 2020 # 5 Years is enough for proof of concept
END_YEAR = 2025
LOCATION_LAT = 33.64
LOCATION_LON = -84.42
OM_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
TWC_URL_BASE = "https://api.weather.com/v1/location/KATL:9:US/observations/historical.json"
TWC_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
OUTPUT_FILE = "katl_sophisticated_data.csv"

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

def fetch_gfs_hourly_features():
    print(f"--- Fetching GFS Hourly Features for KATL ({START_YEAR}-{END_YEAR}) ---")
    
    params = {
        "latitude": LOCATION_LAT,
        "longitude": LOCATION_LON,
        "start_date": f"{START_YEAR}-01-01",
        "end_date": f"{END_YEAR}-12-31",
        "hourly": "temperature_2m",
        "models": "gfs_seamless",
        "temperature_unit": "fahrenheit"
    }
    
    data = fetch_url(OM_URL, params)
    if not data: return None
    
    hourly = data['hourly']
    times = pd.to_datetime(hourly['time'])
    temps = hourly['temperature_2m']
    
    df = pd.DataFrame({'time': times, 'temp': temps})
    
    # Convert to US Eastern Time
    df = df.set_index('time')
    if df.index.tz is None:
        df = df.tz_localize('UTC')
    df = df.tz_convert('America/New_York')
    
    df['Date'] = df.index.date
    df['Hour'] = df.index.hour

    # Handle DST duplicates by taking the mean of conflicting hours
    df = df.groupby(['Date', 'Hour'])['temp'].mean().reset_index()
    
    pivot = df.pivot(index='Date', columns='Hour', values='temp')
    pivot.columns = [f"GFS_{h:02d}" for h in pivot.columns]
    
    print(f"GFS Hourly Processed: {len(pivot)} days")
    return pivot

def fetch_twc_daily_targets():
    print(f"--- Fetching TWC Actuals for KATL ({START_YEAR}-{END_YEAR}) ---")
    
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
                    ts = o.get('valid_time_gmt')
                    dt = pd.to_datetime(ts, unit='s', utc=True).tz_convert('America/New_York')
                    all_obs.append({'Date': dt.date(), 'Temp': o['temp']})
        
        if i % 12 == 0:
            print(f"TWC Progress: {d.year} ({i}/{total})")
        time.sleep(0.1)
        
    df = pd.DataFrame(all_obs)
    if df.empty: return None
    
    daily_max = df.groupby('Date')['Temp'].max()
    daily_max.name = "Target_MaxTemp"
    
    print(f"TWC Actuals Processed: {len(daily_max)} days")
    return daily_max

def main():
    features = fetch_gfs_hourly_features()
    targets = fetch_twc_daily_targets()
    
    if features is None or targets is None:
        print("Failed to fetch data.")
        return
    
    features.index = pd.to_datetime(features.index)
    targets.index = pd.to_datetime(targets.index)
    
    merged = pd.concat([features, targets], axis=1, join='inner')
    
    print(f"Merged Dataset: {len(merged)} days.")
    merged.to_csv(OUTPUT_FILE)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
