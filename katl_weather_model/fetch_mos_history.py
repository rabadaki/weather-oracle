import urllib.request
import json
import csv
import time
import os
import ssl
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Configuration
STATION = "KATL"
MODEL = "GFS"
START_YEAR = 2015
END_YEAR = 2025
RAW_OUTPUT = "katl_mos_raw.csv"
CLEAN_OUTPUT = "katl_mos_history.csv"
BASE_URL = "https://mesonet.agron.iastate.edu/api/1/mos.json"

# Thread-safe lock for writing
csv_lock = threading.Lock()

def fetch_day(date_obj):
    """Fetches matches for a single day (12Z run). Returns list of records."""
    date_str = date_obj.strftime("%Y-%m-%d")
    runtime = f"{date_str}T12:00Z"
    url = f"{BASE_URL}?station={STATION}&model={MODEL}&runtime={runtime}"
    
    # SSL Bypass per thread
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    records = []
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                if 'data' in data:
                    for item in data['data']:
                        record = {
                            'runtime': item.get('runtime'),
                            'ftime': item.get('ftime'),
                            'n_x': item.get('n_x'),
                            'tmp': item.get('tmp'),
                            'dpt': item.get('dpt'),
                            'wsp': item.get('wsp'),
                            'cld': item.get('cld')
                        }
                        records.append(record)
    except Exception as e:
        # print(f"[{date_str}] Error: {e}") # Reduce noise
        pass
        
    return records

def fetch_mos_data_fast():
    print(f"--- Starting FAST MOS Acquisition for {STATION} ({START_YEAR}-{END_YEAR}) ---")
    
    # Generate Date List
    start_date = datetime(START_YEAR, 1, 1)
    end_date = datetime(END_YEAR, 12, 31)
    if end_date > datetime.now():
        end_date = datetime.now() - timedelta(days=1)
        
    date_list = []
    curr = start_date
    while curr <= end_date:
        date_list.append(curr)
        curr += timedelta(days=1)
        
    total_days = len(date_list)
    print(f"Target: {total_days} daily model runs.")
    
    # Initialize Raw CSV
    headers = ['runtime', 'ftime', 'n_x', 'tmp', 'dpt', 'wsp', 'cld']
    with open(RAW_OUTPUT, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

    all_raw_data = [] # Keep in memory for final processing too
    
    # Execute in Parallel
    completed = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_date = {executor.submit(fetch_day, d): d for d in date_list}
        
        for future in as_completed(future_to_date):
            day_records = future.result()
            completed += 1
            if completed % 50 == 0:
                print(f"Progress: {completed}/{total_days} ({completed/total_days:.1%})")
            
            if day_records:
                with csv_lock:
                    with open(RAW_OUTPUT, 'a', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=headers)
                        writer.writerows(day_records)
                all_raw_data.extend(day_records)
                
    print(f"--- Fetch Complete. Processed {len(all_raw_data)} raw MOS lines. ---")
    process_clean_history(all_raw_data)

def process_clean_history(records):
    print("--- Processing Raw Data into Training Format ---")
    
    grouped = {}
    for r in records:
        rt = r['runtime']
        if rt not in grouped: grouped[rt] = []
        grouped[rt].append(r)
        
    clean_rows = []
    
    for rt_str, group in grouped.items():
        try:
            # Resilient parsing
            try:
                runtime_dt = datetime.strptime(rt_str, "%Y-%m-%d %H:%M")
            except ValueError:
                runtime_dt = datetime.strptime(rt_str, "%Y-%m-%dT%H:%M:%S")
        except:
            continue
                 
        # Target: Runtime + 36h = Day+1 Forecast (Jan 1 Run -> Jan 2 Max)
        target_valid_time = (runtime_dt.replace(hour=0, minute=0, second=0) + timedelta(days=2))
        
        best_match = None
        for r in group:
            ft_str = r['ftime']
            if not ft_str: continue
            try:
                ft_dt = datetime.strptime(ft_str, "%Y-%m-%d %H:%M")
            except:
                continue
            
            if ft_dt == target_valid_time:
                best_match = r
                break
                
        if best_match and best_match['n_x'] is not None:
            pred_date = (runtime_dt + timedelta(days=1)).strftime('%Y-%m-%d')
            clean_rows.append({'Date': pred_date, 'MOS_MaxTemp': best_match['n_x']})
            
    clean_rows.sort(key=lambda x: x['Date'])
    
    with open(CLEAN_OUTPUT, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Date', 'MOS_MaxTemp'])
        writer.writeheader()
        writer.writerows(clean_rows)
        
    print(f"Saved Processed History to {CLEAN_OUTPUT} ({len(clean_rows)} records)")

if __name__ == "__main__":
    fetch_mos_data_fast()
