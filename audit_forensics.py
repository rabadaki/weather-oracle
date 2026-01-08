import pandas as pd
import json
import numpy as np

def audit_integrity(region, model_file, era5_file, model_col_prefix):
    print(f"\n--- Auditing {region} ---")
    
    # Load ERA5 (Truth/Analysis)
    with open(era5_file) as f:
        data = json.load(f)
    era5_df = pd.DataFrame({
        'time': pd.to_datetime(data['hourly']['time']),
        'ERA5': data['hourly']['temperature_2m']
    })
    # Open-Meteo Archive is usually UTC.
    era5_df = era5_df.set_index('time')
    
    # Load My Training Data
    # Index is Date (YYYY-MM-DD). Columns are Hour_00...Hour_23.
    # We need to unpivot it to match ERA5 timestamp stream.
    try:
        my_df = pd.read_csv(model_file)
    except:
        print("Training file not found/readable.")
        return

    # Filter to Jan 1-7 2024
    my_df['Date'] = pd.to_datetime(my_df['Date'])
    mask = (my_df['Date'] >= '2024-01-01') & (my_df['Date'] <= '2024-01-07')
    sample = my_df.loc[mask].copy()
    
    if sample.empty:
        print("No overlapping dates found in training data.")
        return

    # Unpivot: Date + Col -> Timestamp
    # Columns like GFS_00, GFS_01...
    comparison_rows = []
    
    for _, row in sample.iterrows():
        d = row['Date']
        for h in range(24):
            col = f"{model_col_prefix}{h:02d}"
            if col in row:
                val = row[col]
                # Construct timestamp. Beware Timezones!
                # My data is Local Time. ERA5 is UTC (usually).
                # Wait, Open-Meteo Archive is UTC by default.
                # My script converted to Local.
                # I need to be careful here. 
                # Simplest check: Just check the *Daily Max*.
                # If Daily Max(Model) == Daily Max(ERA5), it's leakage.
                pass
    
    # Let's do Daily Max Comparison (Robust to TZ shifting)
    # ERA5 Daily Max
    era5_df['Date'] = era5_df.index.date
    # Note: ERA5 date bins might be UTC. My data is Local.
    # This might introduce a shift.
    # Let's just print the values.
    
    era5_max = era5_df.groupby('Date')['ERA5'].max()
    
    # My Model Max
    # My CSV has rows by Date.
    # Recalculate max from hourly cols
    hourly_cols = [c for c in sample.columns if c.startswith(model_col_prefix)]
    sample['Model_Max'] = sample[hourly_cols].max(axis=1)
    
    print("Log: Daily Max Comparison (Fahrenheit if converted, C if raw ERA5)")
    # ERA5 defaults to Celsius unless requested.
    # My Curl didn't specify units for ERA5 -> It's Celsius.
    # My Training Data is Fahrenheit.
    # I must convert ERA5 C -> F.
    
    for d in sample['Date']:
        d_date = d.date()
        if d_date in era5_max.index:
            e_c = era5_max.loc[d_date]
            e_f = (e_c * 9/5) + 32
            
            m_f = sample.loc[sample['Date'] == d, 'Model_Max'].values[0]
            
            diff = abs(m_f - e_f)
            print(f"{d_date}: Model {m_f:.2f} F vs ERA5 {e_f:.2f} F (Diff: {diff:.2f})")

def main():
    audit_integrity("Atlanta", "katl_sophisticated_data.csv", "era5_atlanta.json", "GFS_")
    audit_integrity("Seoul", "rksi_sophisticated_data.csv", "era5_seoul.json", "JMA_")

if __name__ == "__main__":
    main()
