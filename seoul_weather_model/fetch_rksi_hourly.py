import urllib.request
import json
import csv
import ssl
import time
import datetime
from collections import defaultdict

# API Key (Re-using existing key)
API_KEY = "e1f10a1e78da46f5b10a1e78da96f525" 

# Target: Incheon International Airport (RKSI)
# Format: RKSI:9:KR (Standard TWC ICAO format)
LOCATION = "RKSI:9:KR"

def fetch_month_data(year, month):
    start_date = f"{year}{month:02d}01"
    
    # End day logic
    if month in [1, 3, 5, 7, 8, 10, 12]: end_day = 31
    elif month == 2: 
        if year % 4 == 0: end_day = 29
        else: end_day = 28
    else: end_day = 30
    
    end_date = f"{year}{month:02d}{end_day}"
    
    print(f"Fetching {LOCATION} {start_date} - {end_date}...")
    
    url = f"https://api.weather.com/v1/location/{LOCATION}/observations/historical.json?units=e&startDate={start_date}&endDate={end_date}&apiKey={API_KEY}"
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(url, context=ctx) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode('utf-8'))
                return data.get('observations', [])
            else:
                print(f"Error {response.getcode()} for {start_date}")
                return []
    except Exception as e:
        print(f"Failed to fetch {start_date}: {e}")
        return []

def process_observations_hourly(observations):
    hourly_data = []
    
    for obs in observations:
        temp = obs.get('temp')
        if temp is None: continue
            
        ts = obs.get('valid_time_gmt')
        dt_utc = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
        
        # Korea Standard Time (KST) is UTC +9
        # KST does NOT observe DST. Fixed offset.
        offset = 9
        dt_local = dt_utc + datetime.timedelta(hours=offset)
        
        local_date = dt_local.strftime("%Y-%m-%d")
        local_time = dt_local.strftime("%H:%M:%S")
        hour = dt_local.hour
        
        pressure = obs.get('pressure', "")
        wspd = obs.get('wspd', "")
        rh = obs.get('rh', "")
        precip = obs.get('precip_hrly', 0.0)
        
        hourly_data.append({
            'Date': local_date,
            'Time': local_time,
            'Hour': hour,
            'Temp': temp,
            'Pressure': pressure,
            'Wind': wspd,
            'RH': rh,
            'Precip': precip
        })
        
    return hourly_data

def bulk_fetch_hourly(start_year=2024, end_year=2026):
    all_rows = []
    print(f"Starting Hourly fetch for {start_year}-{end_year}...")
    
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            if year == 2026 and month > 1: break 
            
            obs = fetch_month_data(year, month)
            rows = process_observations_hourly(obs)
            all_rows.extend(rows)
            print(f"  Fetched {len(rows)} hours for {year}-{month:02d}")
            time.sleep(0.5)
            
    csv_file = "/Users/Amos/seoul_weather_model/rksi_hourly.csv"
    keys = ['Date', 'Time', 'Hour', 'Temp', 'Pressure', 'Wind', 'RH', 'Precip']
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(all_rows)
        
    print(f"Saved {len(all_rows)} hourly records to {csv_file}")

if __name__ == "__main__":
    # Fetch 10 years of history for robust seasonality training
    bulk_fetch_hourly(2015, 2025)
