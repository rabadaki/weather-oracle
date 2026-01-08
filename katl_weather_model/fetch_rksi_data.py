import urllib.request
import urllib.parse
import pandas as pd
import json
import time
from datetime import datetime
import numpy as np
import ssl

# Config
OM_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
TWC_URL_BASE = "https://api.weather.com/v1/location/RKSI:9:KR/observations/historical.json"
TWC_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
START_YEAR = 2021
END_YEAR = 2025
OUTPUT_FILE = "rksi_jma_training.csv"

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

def fetch_om_hindcasts():
    print("--- Fetching Open-Meteo GFS Hindcasts (Seoul) ---")
    
    # Lat/Lon for Incheon
    params = {
        "latitude": 37.46,
        "longitude": 126.44,
        "start_date": f"{START_YEAR}-01-01",
        "end_date": f"{END_YEAR}-12-31",
        "hourly": "temperature_2m",
        "models": "jma_gsm",
        "temperature_unit": "fahrenheit" 
    }
    
    data = fetch_url(OM_URL, params)
    if not data: return None
    
    hourly = data['hourly']
    times = hourly['time']
    temps = hourly['temperature_2m']
    
    # DataFrame
    df = pd.DataFrame({'time': times, 'temp': temps})
    df['time'] = pd.to_datetime(df['time'])
    
    # Group by Day -> Max
    # OM returns ISO UTC. Convert to Seoul Local.
    df = df.set_index('time')
    try:
        df = df.tz_localize('UTC')
    except:
        pass 
    df = df.tz_convert('Asia/Seoul')
    
    daily_max = df['temp'].resample('D').max()
    print(f"OM Fetch Success: {len(daily_max)} days.")
    return daily_max

def fetch_twc_actuals():
    print("--- Fetching TWC Observations (Seoul) ---")
    
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
                    # TWC epoch is GMT
                    ts = o.get('valid_time_gmt')
                    dt = pd.to_datetime(ts, unit='s', utc=True).tz_convert('Asia/Seoul')
                    all_obs.append({'time': dt, 'temp': o['temp']})
        
        if i % 10 == 0:
            print(f"TWC Progress: {i}/{total} months")
        time.sleep(0.2)
        
    df = pd.DataFrame(all_obs)
    if df.empty: return None
    
    df = df.set_index('time')
    daily_max = df['temp'].resample('D').max()
    print(f"TWC Fetch Success: {len(daily_max)} days.")
    return daily_max

def main():
    om_series = fetch_om_hindcasts()
    twc_series = fetch_twc_actuals()
    
    if om_series is None or twc_series is None:
        print("Failed to get both sources.")
        return
        
    # Merge
    om_df = om_series.to_frame(name="MOS_MaxTemp")
    twc_df = twc_series.to_frame(name="MaxTemp")
    
    om_df.index = om_df.index.normalize()
    twc_df.index = twc_df.index.normalize()
    
    merged = pd.merge(om_df, twc_df, left_index=True, right_index=True, how='inner')
    merged.index.name = "Date"
    
    print(f"Merged Data: {len(merged)} common days.")
    merged['Bias'] = merged['MaxTemp'] - merged['MOS_MaxTemp']
    print(f"Mean Bias (Seoul): {merged['Bias'].mean():.2f} F")
    
    merged.to_csv(OUTPUT_FILE)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
