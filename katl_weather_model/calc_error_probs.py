import pandas as pd
import numpy as np

# Files
MOS_FILE = "katl_weather_model/katl_mos_history.csv"
ACTUALS_FILE = "katl_weather_model/katl_full_history.csv"

def calc_probs():
    print("--- Probabilistic Error Analysis (KATL 10-Year) ---")
    try:
        mos = pd.read_csv(MOS_FILE)
        actuals = pd.read_csv(ACTUALS_FILE)
    except FileNotFoundError:
        print("Files not found.")
        return

    # Merge
    df = pd.merge(mos, actuals, on="Date")
    df['MOS_MaxTemp'] = pd.to_numeric(df['MOS_MaxTemp'], errors='coerce')
    df['MaxTemp'] = pd.to_numeric(df['MaxTemp'], errors='coerce')
    df.dropna(subset=['MOS_MaxTemp', 'MaxTemp'], inplace=True)
    
    # Error = Actual - Forecast
    # If Forecast is 70, Actual is 71, Error is +1.
    df['Error'] = df['MaxTemp'] - df['MOS_MaxTemp']
    errors = df['Error'].abs()
    
    total = len(df)
    print(f"Total Daily Events: {total}")
    
    # Bucket: +/- 1 F (Total width 2F) - Roughly matching a 1C bucket
    # Note: 1C is 1.8F. So +/- 0.9F is a 1C bucket centered on the prediction.
    # Polymarket buckets are often 2F wide centered on even numbers? Or ranges?
    # Usually "70-72", "72-74". Width is 2F.
    # If we predict 71, and the bucket is 70-72, we win if Actual is 70, 71, 72.
    # So we need to be within ~1F of the center.
    
    within_1 = len(errors[errors <= 1.0])
    within_2 = len(errors[errors <= 2.0])
    within_3 = len(errors[errors <= 3.0])
    
    print(f"\n[Win Probabilities]")
    print(f"Within +/- 1.0 F: {within_1/total:.1%} (Target: Exact Bucket Match)")
    print(f"Within +/- 2.0 F: {within_2/total:.1%} (Target: Neighbor Bucket Safety)")
    print(f"Within +/- 3.0 F: {within_3/total:.1%}")
    
    print(f"\n90% Confidence Interval: +/- {np.percentile(errors, 90):.1f} F")

if __name__ == "__main__":
    calc_probs()
