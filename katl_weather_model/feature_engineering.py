import csv
import math
import datetime
import statistics
import os

# Settings
INPUT_FILE = "katl_full_history.csv"
OUTPUT_FILE = "katl_features.csv"

def create_features():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    print("Loading data...")
    # Read raw data
    data = []
    with open(INPUT_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
            
    # Parse dates and sort just in case
    # Format: YYYY-MM-DD
    # We assume sorted from previous step, but let's be safe if we were in pandas. 
    # In pure python, list is likely already sorted if file was sorted.
    
    # Helper for rolling stats
    def get_rolling_stats(values, window=7):
        # values is list of floats
        # returns (mean, std) list
        # Be careful with list bounds
        means = []
        stds = []
        for i in range(len(values)):
            if i < window:
                means.append(None)
                stds.append(None)
                continue
            
            slice_window = values[i-window : i] # T-window to T-1
            m = statistics.mean(slice_window)
            if len(slice_window) > 1:
                s = statistics.stdev(slice_window)
            else:
                s = 0.0
            means.append(m)
            stds.append(s)
        return means, stds

    # Extract columns
    dates = []
    max_temps = []
    min_temps = []
    pressures = [] 
    winds = []
    rhs = []
    precips = []
    
    for row in data:
        dates.append(row['Date'])
        max_temps.append(float(row['MaxTemp']) if row['MaxTemp'] else None)
        min_temps.append(float(row['MinTemp']) if row['MinTemp'] else None)
        
        # New cols - handle empty strings
        p = float(row['MeanPressure']) if row.get('MeanPressure') else None
        w = float(row['MaxWind']) if row.get('MaxWind') else None
        h = float(row['MeanRH']) if row.get('MeanRH') else None
        pr = float(row['TotalPrecip']) if row.get('TotalPrecip') else 0.0
        
        pressures.append(p)
        winds.append(w)
        rhs.append(h)
        precips.append(pr)

    # Generate Features
    output_rows = []
    
    # Helper for rolling stats with None handling
    def get_rolling_stats_safe(values, window=7):
        means = []
        for i in range(len(values)):
            if i < window:
                means.append(None)
                continue
            slice_window = values[i-window : i]
            # Filter Nones
            clean = [x for x in slice_window if x is not None]
            if len(clean) > window // 2: # At least half data
                means.append(statistics.mean(clean))
            else:
                means.append(None)
        return means

    # Rolling for Temps (std included) and others (mean only)
    # Note: re-using get_rolling_stats from before for temps which assumes no Nones? 
    # Let's use the safe one for everything or ensure data quality.
    # Our data fetcher is robust but let's be safe.
    
    roll_mean_temp, roll_std_temp = get_rolling_stats(max_temps, 7) # Uses the old helper
    roll_mean_press = get_rolling_stats_safe(pressures, 3) # Shorter window for pressure changes?
    roll_mean_rh = get_rolling_stats_safe(rhs, 3)
    
    header = [
        "Date", "MaxTemp", "MinTemp", "DayOfYear", "Month", "Year", 
        "DayOfYear_Sin", "DayOfYear_Cos",
        "Lag1", "Lag2", "Lag3", "Lag7",
        "RollMean7", "RollStd7",
        "Pressure_Lag1", "Wind_Lag1", "RH_Lag1", "Precip_Lag1",
        "Pressure_Trend", # Lag1 - Lag2
        "Target_T1"
    ]
    
    for i in range(len(dates)):
        # Calculate Date Features
        dt = datetime.datetime.strptime(dates[i], "%Y-%m-%d")
        doy = dt.timetuple().tm_yday
        month = dt.month
        year = dt.year
        
        sin_doy = math.sin(2 * math.pi * doy / 365.25)
        cos_doy = math.cos(2 * math.pi * doy / 365.25)
        
        # Lags
        lag1 = max_temps[i-1] if i >= 1 else None
        lag2 = max_temps[i-2] if i >= 2 else None
        lag3 = max_temps[i-3] if i >= 3 else None
        lag7 = max_temps[i-7] if i >= 7 else None
        
        # New Lags
        p_lag1 = pressures[i-1] if i >= 1 else None
        p_lag2 = pressures[i-2] if i >= 2 else None
        w_lag1 = winds[i-1] if i >= 1 else None
        h_lag1 = rhs[i-1] if i >= 1 else None
        pr_lag1 = precips[i-1] if i >= 1 else None
        
        # Derived
        p_trend = (p_lag1 - p_lag2) if (p_lag1 is not None and p_lag2 is not None) else None
        
        # Rolling
        rm7 = roll_mean_temp[i]
        rs7 = roll_std_temp[i]
        
        # Targets
        target_t1 = max_temps[i+1] if i + 1 < len(max_temps) else None
        
        row_dict = {
            "Date": dates[i],
            "MaxTemp": max_temps[i],
            "MinTemp": min_temps[i],
            "DayOfYear": doy,
            "Month": month,
            "Year": year,
            "DayOfYear_Sin": sin_doy,
            "DayOfYear_Cos": cos_doy,
            "Lag1": lag1,
            "Lag2": lag2,
            "Lag3": lag3,
            "Lag7": lag7,
            "RollMean7": rm7,
            "RollStd7": rs7,
            "Pressure_Lag1": p_lag1,
            "Wind_Lag1": w_lag1,
            "RH_Lag1": h_lag1,
            "Precip_Lag1": pr_lag1,
            "Pressure_Trend": p_trend,
            "Target_T1": target_t1
        }
        output_rows.append(row_dict)

    print(f"Total rows: {len(output_rows)}")
    
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(output_rows)
        
    print(f"Saved features to {OUTPUT_FILE}")


if __name__ == "__main__":
    create_features()
