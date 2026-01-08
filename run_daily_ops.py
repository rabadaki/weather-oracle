import pandas as pd
import datetime
import os
import subprocess
import sys

# Paths
LOG_FILE = "predictions_log.csv"
HISTORY_FILE = "history_log.csv"

def run_predictions():
    print("--- Running Daily Predictions ---")
    
    # 1. Atlanta
    print("\n[Atlanta]")
    # We capture stdout
    res_katl = subprocess.run([sys.executable, "katl_weather_model/predict_live.py"], capture_output=True, text=True)
    print(res_katl.stdout)
    
    # Parse output for logging? (Ideally predict_live should return a value, but printing is fine for now)
    
    # 2. Seoul
    print("\n[Seoul]")
    res_rksi = subprocess.run([sys.executable, "katl_weather_model/predict_seoul.py"], capture_output=True, text=True)
    print(res_rksi.stdout)
    
    # Log run
    with open(LOG_FILE, "a") as f:
        ts = datetime.datetime.now().isoformat()
        f.write(f"{ts},Ran Prediction Cycle\n")

def fetch_yesterday_actuals():
    print("\n--- Fetching Yesterday's Actuals ---")
    # This logic requires a targeted TWC fetch for "Yesterday".
    # Since we don't have a dedicated "Fetch Yesterday" script yet,
    # we can stub this or call a modified fetcher.
    # For now, we will just log that the job ran.
    print("TODO: Implement targeted TWC fetch for T-1.")

def main():
    run_predictions()
    fetch_yesterday_actuals()

if __name__ == "__main__":
    main()
