import urllib.request
import json
import csv
import datetime
import time
import ssl
from collections import defaultdict

API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
LOCATION = "KATL:9:US"
BASE_URL = f"https://api.weather.com/v1/location/{LOCATION}/observations/historical.json"

def fetch_month_data(year, month):
    # Construct startDate and endDate
    # Format: YYYYMMDD
    start_date = datetime.date(year, month, 1)
    # trick to get last day:
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    end_date = next_month - datetime.timedelta(days=1)
    
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    url = f"{BASE_URL}?apiKey={API_KEY}&units=e&startDate={start_str}&endDate={end_str}"
    print(f"Fetching {start_str} - {end_str}...")
    
    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=context) as response:
            if response.status != 200:
                print(f"Error {response.status}: {response.read()}")
                return []
            data = json.loads(response.read().decode('utf-8'))
            return data.get('observations', [])
    except Exception as e:
        print(f"Exception fetching {url}: {e}")
        return []

def process_observations(observations, timezone_offset=-5):
    # KATL is Eastern Time.
    # Standard: UTC-5. DST: UTC-4.
    # We should use the 'valid_time_gmt' and convert nicely.
    # For now, hardcoded offset is risky. 
    # Better: The API returns `valid_time_gmt`.
    # We can rely on the fact that for "Daily High", the Date matters.
    # Let's try to infer offset or use valid_time_gmt with a naive shift for EST/EDT logic
    # or just use the API's provided fields if any (class: observation often has no local time string).
    
    daily_stats = defaultdict(list)
    daily_pressure = defaultdict(list)
    daily_rh = defaultdict(list)
    daily_wspd = defaultdict(list)
    daily_precip = defaultdict(list)
    
    for obs in observations:
        temp = obs.get('temp')
        if temp is None:
            continue
            
        ts = obs.get('valid_time_gmt')
        dt_utc = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
        
        # Approximate Local Time (same logic as before)
        is_dst = False
        if (dt_utc.month > 3 and dt_utc.month < 11):
            is_dst = True
        elif dt_utc.month == 3:
            if dt_utc.day >= 10: is_dst = True
        elif dt_utc.month == 11:
            if dt_utc.day < 2: is_dst = True
            
        if is_dst: frame_offset = -4
        else: frame_offset = -5
            
        dt_local = dt_utc + datetime.timedelta(hours=frame_offset)
        day_key = dt_local.strftime("%Y-%m-%d")
        
        daily_stats[day_key].append(temp)
        
        if obs.get('pressure'): daily_pressure[day_key].append(obs.get('pressure'))
        if obs.get('rh'): daily_rh[day_key].append(obs.get('rh'))
        if obs.get('wspd'): daily_wspd[day_key].append(obs.get('wspd'))
        if obs.get('precip_hrly'): daily_precip[day_key].append(obs.get('precip_hrly'))
        
    results = {}
    for day, temps in daily_stats.items():
        # Aggregation
        try:
             mean_pressure = sum(daily_pressure[day])/len(daily_pressure[day]) if daily_pressure[day] else None
             mean_rh = sum(daily_rh[day])/len(daily_rh[day]) if daily_rh[day] else None
             max_wspd = max(daily_wspd[day]) if daily_wspd[day] else 0.0
             total_precip = sum(daily_precip[day]) if daily_precip[day] else 0.0
        except:
             mean_pressure = None
             mean_rh = None
             max_wspd = None
             total_precip = None

        results[day] = {
            'max': max(temps),
            'min': min(temps),
            'count': len(temps),
            'pressure': mean_pressure,
            'rh': mean_rh,
            'wspd': max_wspd,
            'precip': total_precip
        }
    return results

def bulk_fetch_and_save(start_year=2015, end_year=2026):
    all_daily_data = {}
    print(f"Starting bulk fetch for {start_year}-{end_year}...")
    
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            if year == 2026 and month > 1: break
            obs = fetch_month_data(year, month)
            daily = process_observations(obs)
            all_daily_data.update(daily)
            time.sleep(0.5) 
            
    # Save to CSV
    csv_file = "katl_full_history.csv"
    print(f"Saving {len(all_daily_data)} days to {csv_file}...")
    sorted_days = sorted(all_daily_data.keys())
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "MaxTemp", "MinTemp", "ObsCount", "MeanPressure", "MeanRH", "MaxWind", "TotalPrecip"])
        for day in sorted_days:
            stats = all_daily_data[day]
            writer.writerow([
                day, stats['max'], stats['min'], stats['count'],
                f"{stats['pressure']:.2f}" if stats['pressure'] else "",
                f"{stats['rh']:.1f}" if stats['rh'] else "",
                stats['wspd'],
                f"{stats['precip']:.2f}"
            ])
            
    # Jan 6 stats print (omitted for brevity, main loop handles it)

if __name__ == "__main__":
    bulk_fetch_and_save(2015, 2026)
