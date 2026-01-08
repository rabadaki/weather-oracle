import pandas as pd
import numpy as np

FILE = "rksi_training_data.csv"

def check_seoul():
    print("--- Seoul (RKSI) Accuracy Check [2021-2025] ---")
    df = pd.read_csv(FILE, index_col=0)
    
    # Error = Actual - Forecast
    df['Error'] = df['MaxTemp'] - df['MOS_MaxTemp']
    mae = df['Error'].abs().mean()
    bias = df['Error'].mean()
    
    print(f"Total Days: {len(df)}")
    print(f"Mean Absolute Error (MAE): {mae:.2f} F")
    print(f"Mean Bias: {bias:.2f} F")
    
    # Win Rates
    total = len(df)
    win_1 = len(df[df['Error'].abs() <= 1.0])
    win_2 = len(df[df['Error'].abs() <= 2.0])
    
    print(f"Win Rate (+/- 1F): {win_1/total:.1%}")
    print(f"Win Rate (+/- 2F): {win_2/total:.1%}")
    
    if mae > 4.0:
        print("VERDICT: Poor Model (Like Pure ML).")
    elif mae > 3.0:
        print("VERDICT: Decent Model.")
    else:
        print("VERDICT: Excellent Model (Betable).")

if __name__ == "__main__":
    check_seoul()
