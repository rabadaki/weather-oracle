import pandas as pd
import numpy as np

# Use the file we just created
INPUT_FILE = "/Users/Amos/seoul_weather_model/rksi_hourly.csv"

def get_season(month):
    # Korea Seasons
    # Winter: Dec-Feb
    # Spring: Mar-May
    # Summer: Jun-Aug
    # Fall: Sep-Nov
    if month in [12, 1, 2]: return 'Winter'
    elif month in [3, 4, 5]: return 'Spring'
    elif month in [6, 7, 8]: return 'Summer'
    else: return 'Fall'

def analyze_seoul():
    print("Loading RKSI data...")
    try:
        df = pd.read_csv(INPUT_FILE)
    except Exception as e:
        print(f"Error: {e}")
        return

    df['Date'] = pd.to_datetime(df['Date'])
    df['Temp'] = pd.to_numeric(df['Temp'], errors='coerce')
    df = df.dropna(subset=['Temp'])
    
    # Identify Peak Hour
    daily_peaks = []
    
    for date, group in df.groupby('Date'):
        idx_max = group['Temp'].idxmax()
        peak_hour = group.loc[idx_max, 'Hour']
        daily_peaks.append({
            'Date': date,
            'PeakHour': peak_hour,
            'Season': get_season(date.month)
        })
        
    res_df = pd.DataFrame(daily_peaks)
    
    # Global
    print("\n--- Seoul (RKSI) Peak Hour Distribution (UTC+9) ---")
    counts = res_df['PeakHour'].value_counts().sort_index()
    total = len(res_df)
    cumulative = 0
    cutoff_95 = None
    
    print(f"{'Hour':<4} | {'Count':<5} | {'Pct':<5} | {'CumPct':<6}")
    print("-" * 30)
    for h in sorted(counts.index):
        c = counts[h]
        pct = (c / total) * 100
        cumulative += pct
        print(f"{h:02d}:00 | {c:<5} | {pct:<5.1f} | {cumulative:<6.1f}%")
        
        if cumulative >= 95 and cutoff_95 is None:
            cutoff_95 = h
            
    print(f"\n=> 95% of Daily Highs occur by {cutoff_95:02d}:00 KST.")
    
    # Seasonality
    print("\n--- Seasonal Analysis (95% Cutoff) ---")
    for s in ['Winter', 'Spring', 'Summer', 'Fall']:
        s_data = res_df[res_df['Season'] == s]
        if s_data.empty: continue
        
        counts = s_data['PeakHour'].value_counts().sort_index()
        total = len(s_data)
        cum = 0
        cut = None
        for h in sorted(counts.index):
            cum += (counts[h] / total) * 100
            if cum >= 95:
                cut = h
                break
        mode = s_data['PeakHour'].mode()[0]
        print(f"{s:<6}: 95% by {cut:02d}:00. (Mode: {mode:02d}:00)")

if __name__ == "__main__":
    analyze_seoul()
