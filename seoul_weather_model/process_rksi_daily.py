import pandas as pd
import numpy as np

INPUT_FILE = "/Users/Amos/seoul_weather_model/rksi_hourly.csv"
OUTPUT_FILE = "/Users/Amos/seoul_weather_model/rksi_daily.csv"

def aggregate_daily():
    print("Loading hourly data...")
    try:
        df = pd.read_csv(INPUT_FILE)
    except Exception as e:
        print(f"Error: {e}")
        return

    df['Date'] = pd.to_datetime(df['Date'])
    df['Temp'] = pd.to_numeric(df['Temp'], errors='coerce')
    df['Pressure'] = pd.to_numeric(df['Pressure'], errors='coerce')
    df['Wind'] = pd.to_numeric(df['Wind'], errors='coerce')
    df['RH'] = pd.to_numeric(df['RH'], errors='coerce')
    
    # Filter valid temps
    df = df.dropna(subset=['Temp'])
    
    print(f"Aggregating {len(df)} hourly records...")
    
    daily_stats = []
    
    for date, group in df.groupby('Date'):
        # Daily Stats
        max_temp = group['Temp'].max()
        min_temp = group['Temp'].min()
        mean_pressure = group['Pressure'].mean()
        max_wind = group['Wind'].max()
        mean_rh = group['RH'].mean()
        
        daily_stats.append({
            'Date': date,
            'MaxTemp': max_temp,
            'MinTemp': min_temp,
            'MeanPressure': mean_pressure,
            'MaxWind': max_wind,
            'MeanRH': mean_rh
        })
        
    daily_df = pd.DataFrame(daily_stats).sort_values('Date')
    daily_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(daily_df)} daily records to {OUTPUT_FILE}")

if __name__ == "__main__":
    aggregate_daily()
