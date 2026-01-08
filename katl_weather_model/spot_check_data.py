import pandas as pd
import random

def spot_check():
    print("--- DATA SPOT CHECK (User Verification) ---")
    
    # 1. Seoul (RKSI)
    print("\n[Seoul (RKSI) - TWC Actuals]")
    try:
        df_seoul = pd.read_csv("rksi_training_data.csv")
        sample_seoul = df_seoul.sample(3)
        for _, row in sample_seoul.iterrows():
            print(f"Date: {row['Date']} | MaxTemp: {row['MaxTemp']:.1f} F")
    except Exception as e:
        print(f"Error reading Seoul data: {e}")

    # 2. Atlanta (KATL) - TWC Actuals
    print("\n[Atlanta (KATL) - TWC Actuals]")
    try:
        # Check available files.
        # usually katl_weather_model/katl_full_history.csv
        df_katl = pd.read_csv("katl_weather_model/katl_full_history.csv")
        sample_katl = df_katl.sample(3)
        for _, row in sample_katl.iterrows():
            print(f"Date: {row['Date']} | MaxTemp: {row['MaxTemp']} F")
    except Exception as e:
        print(f"Error reading Atlanta data: {e}")

if __name__ == "__main__":
    spot_check()
