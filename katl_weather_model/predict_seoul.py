import pandas as pd
import numpy as np
import xgboost as xgb
import json
import urllib.request
import urllib.parse
import datetime
import ssl
import sys

# --- Settings ---
API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
LOCATION = "RKSI:9:KR" # Incheon Airport
MODEL_PATH = "rksi_advanced_model.json"

# --- Helpers ---
def fetch_url(url, params=None):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=10) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
    except Exception as e:
        print(f"Fetch Error: {e} for {url}")
        return None

def fetch_jma_hourly_tomorrow():
    tz_seoul = datetime.timezone(datetime.timedelta(hours=9))
    now_seoul = datetime.datetime.now(tz_seoul)
    tomorrow = now_seoul + datetime.timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    
    print(f"Fetching JMA GSM Hourly Forecast for Seoul (Date: {tomorrow_str})...")
    
    params = {
        "latitude": 37.46,
        "longitude": 126.44,
        "hourly": "temperature_2m",
        "start_date": tomorrow_str,
        "end_date": tomorrow_str,
        "models": "jma_gsm",
        "temperature_unit": "fahrenheit"
    }
    
    om_url = "https://api.open-meteo.com/v1/forecast"
    data = fetch_url(om_url, params)
    
    if not data: return None, None
    
    # Process Hourly
    hourly = data['hourly']
    # We expect 24 hours. "time" is ISO.
    temps = hourly['temperature_2m']
    
    if len(temps) != 24:
        print(f"Warning: Expected 24 hours, got {len(temps)}")
        # If partial, maybe pad or fail? Failing is safer.
        if len(temps) < 24: return None, None
    
    return temps, tomorrow

def predict_seoul():
    print(f"--- Seoul (RKSI) Advanced Prediction Service ---")
    
    # 1. Fetch
    hourly_temps, target_date = fetch_jma_hourly_tomorrow()
    if not hourly_temps:
        print("❌ Failed to fetch JMA Hourly.")
        return
        
    # 2. Engineer Features
    # Create a Series indexed 0..23
    s = pd.Series(hourly_temps) # 0 to 23
    
    # Base Stats
    fcst_max = s.max()
    fcst_min = s.min()
    fcst_mean = s.mean()
    fcst_range = fcst_max - fcst_min
    
    # Slopes
    # Need to handle index access safely
    # JMA_08, JMA_12, JMA_15, JMA_16, JMA_20
    morning_slope = s[12] - s[8]
    peak_slope = s[15] - s[12]
    evening_slope = s[20] - s[16]
    
    # Seasonality
    doy = target_date.timetuple().tm_yday
    sin_doy = np.sin(2 * np.pi * doy / 365.25)
    cos_doy = np.cos(2 * np.pi * doy / 365.25)
    
    # Specific Hours
    jma_12 = s[12]
    jma_13 = s[13]
    jma_14 = s[14]
    jma_15 = s[15]
    
    # Construct Feature DataFrame (Single Row)
    # Order must match training list exactly!
    # Features from training:
    # 'Fcst_Max', 'Fcst_Min', 'Fcst_Mean', 'Fcst_Range',
    # 'Morning_Slope', 'Peak_Slope', 'Evening_Slope',
    # 'Sin_DOY', 'Cos_DOY',
    # 'JMA_12', 'JMA_13', 'JMA_14', 'JMA_15'
    
    features = pd.DataFrame([{
        'Fcst_Max': fcst_max,
        'Fcst_Min': fcst_min,
        'Fcst_Mean': fcst_mean,
        'Fcst_Range': fcst_range,
        'Morning_Slope': morning_slope,
        'Peak_Slope': peak_slope,
        'Evening_Slope': evening_slope,
        'Sin_DOY': sin_doy,
        'Cos_DOY': cos_doy,
        'JMA_12': jma_12,
        'JMA_13': jma_13,
        'JMA_14': jma_14,
        'JMA_15': jma_15
    }])
    
    # 3. Load Model
    try:
        model = xgb.Booster()
        model.load_model(MODEL_PATH)
    except Exception as e:
        print(f"Error loading model {MODEL_PATH}: {e}")
        return
        
    # 4. Predict
    dtest = xgb.DMatrix(features)
    pred_val = model.predict(dtest)[0]
    
    # Convert to Celsius for Display
    pred_c = (pred_val - 32) * 5/9
    raw_c = (fcst_max - 32) * 5/9
    
    print(f"Target Date: {target_date.date()}")
    print(f"Raw JMA Max: {raw_c:.2f} C ({fcst_max:.2f} F)")
    print(f"✅ MODEL PREDICTION: {pred_c:.2f} C")
    print("---------------------------------------")
    
    return {
        "prediction_c": pred_c,
        "prediction_f": pred_val,
        "date": target_date.strftime("%Y-%m-%d"),
        "components": {
            "JMA_Raw_C": raw_c,
            "JMA_Raw_F": fcst_max,
            "Pure_ML_C": pred_c
        }
    }

if __name__ == "__main__":
    predict_seoul()
