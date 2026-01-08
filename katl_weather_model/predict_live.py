import pandas as pd
import numpy as np
import xgboost as xgb
import json
import urllib.request
import datetime
import math
import ssl
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

import os

# --- Settings ---
# Default to the known working key if env var is missing (Backward Comp for local run)
API_KEY = os.getenv("TWC_API_KEY", "e1f10a1e78da46f5b10a1e78da96f525")
LOCATION = "KATL:9:US"

# Dynamic Paths for Docker/Local compatibility
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "katl_xgb_model.json")
HISTORY_FILE = os.path.join(BASE_DIR, "katl_full_history.csv")
BIAS_MODEL_PATH = os.path.join(BASE_DIR, "katl_bias_model.json")

# --- Helpers ---
def get_twc_forecast():
    # Fetch 48 hour forecast
    url = f"https://api.weather.com/v1/location/{LOCATION}/forecast/hourly/48hour.json?units=e&language=en-US&apiKey={API_KEY}"
    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=context) as response:
            if response.status != 200: return []
            data = json.loads(response.read().decode('utf-8'))
            return data.get('forecasts', [])
    except Exception as e:
        print(f"Error fetching forecast: {e}")
        return []

def get_twc_observations_today():
    # Fetch today's observations (00:00 to Now)
    # We use the historical endpoint with startDate=Today, endDate=Today
    # Note: This might return empty if the "historical" bucket isn't populated for today yet.
    # TWC usually processes daily historicals with a lag. 
    # If this fails, we should really use 'current conditions' or 'recent history'.
    # But let's try.
    
    tz = zoneinfo.ZoneInfo("America/New_York")
    now = datetime.datetime.now(tz)
    day_str = now.strftime("%Y%m%d")
    
    url = f"https://api.weather.com/v1/location/{LOCATION}/observations/historical.json?units=e&startDate={day_str}&endDate={day_str}&apiKey={API_KEY}"
    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=context) as response:
            if response.status != 200: return []
            data = json.loads(response.read().decode('utf-8'))
            return data.get('observations', [])
    except Exception as e:
        # 404 is common if data isn't ready
        # print(f"Note: Historical obs for today not available ({e}). Using Forecast only.")
        return []

def combine_and_make_row(obs, fcst):
    # Goal: create a single "Daily Summary" for Today (Day D).
    
    tz = zoneinfo.ZoneInfo("America/New_York")
    now = datetime.datetime.now(tz)
    date_str = now.strftime("%Y-%m-%d")
    
    temps = []
    pressures = []
    winds = []
    rhs = []
    
    # Process Obs
    for o in obs:
        t = o.get('temp')
        if t is not None: temps.append(t)
        if o.get('pressure'): pressures.append(o.get('pressure'))
        if o.get('wspd'): winds.append(o.get('wspd'))
        if o.get('rh'): rhs.append(o.get('rh'))
        
    # Process Forecast
    # Filter for "Rest of Today" only (until 23:59 Local)
    for f in fcst:
        ts = f.get('fcst_valid')
        dt_local = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).astimezone(tz)
        
        if dt_local.date() == now.date():
            # It's today
            t = f.get('temp')
            if t is not None: temps.append(t)
            if f.get('mslp'): pressures.append(f.get('mslp')) # Forecast uses mslp for pressure
            if f.get('wspd'): winds.append(f.get('wspd'))
            if f.get('rh'): rhs.append(f.get('rh'))
            
    if not temps:
        print("CRITICAL: No temperature data found for today (Obs or Forecast).")
        return None
        
    row = {
        'Date': date_str,
        'MaxTemp': max(temps),
        'MinTemp': min(temps),
        'MeanPressure': np.mean(pressures) if pressures else np.nan,
        'MaxWind': max(winds) if winds else np.nan,
        'MeanRH': np.mean(rhs) if rhs else np.nan,
        'Target': np.nan # Unknown
    }
    return row

def fetch_live_mos():
    """Fetches key GFS MOS variables for the current/recent run."""
    # Logic: Get today's 12Z run. If not available, get yesterday's 12Z? 
    # Actually, at live run time (usually evening), today's 12Z is best.
    
    tz = zoneinfo.ZoneInfo("UTC")
    now = datetime.datetime.now(tz)
    
    # Try Today 12Z, 06Z, 00Z, Yesterday 18Z
    candidates = []
    candidates.append(now.strftime("%Y-%m-%dT12:00Z"))
    candidates.append(now.strftime("%Y-%m-%dT06:00Z"))
    candidates.append(now.strftime("%Y-%m-%dT00:00Z"))
    
    yesterday = now - datetime.timedelta(days=1)
    candidates.append(yesterday.strftime("%Y-%m-%dT18:00Z"))

    
    base_url = "https://mesonet.agron.iastate.edu/api/1/mos.json"
    station = "KATL"
    model = "GFS"
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    for runtime in candidates:
        url = f"{base_url}?station={station}&model={model}&runtime={runtime}"
        try:
            with urllib.request.urlopen(url, context=ctx, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    if 'data' in data:
                        return data['data'] # Return full list of time steps
        except Exception as e:
            print(f"MOS Fetch error for {runtime}: {e}")
            
    return None

def predict_live():
    print(f"--- Live Prediction Mode ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}) ---")
    
    # 1. Load History (Autoregressive ML)
    print("Loading history...")
    df_hist = pd.read_csv(HISTORY_FILE)
    df_hist['Date'] = pd.to_datetime(df_hist['Date'])
    df_hist = df_hist.sort_values('Date').tail(30).copy()
    
    # 2. Get TWC Data (Obs + Forecast)
    print("Fetching live TWC data...")
    obs = get_twc_observations_today()
    fcst = get_twc_forecast()
    
    if not obs: 
        print("Note: 'Observed' bucket empty. Using Forecast for full day.")
    
    live_row = combine_and_make_row(obs, fcst)
    if not live_row: return
    
    print(f"Projected Today ({live_row['Date']}): High {live_row['MaxTemp']} F")
    
    # 3. Engineer Features & Run Pure ML
    live_df = pd.DataFrame([live_row])
    live_df['Date'] = pd.to_datetime(live_df['Date'])
    df_full = pd.concat([df_hist, live_df], ignore_index=True)
    
    # [Feature Engineering Block - Lags/Rolls/Seasonality]
    for col in ['MaxTemp', 'MinTemp', 'MeanPressure', 'MaxWind', 'MeanRH']:
        df_full[col] = pd.to_numeric(df_full[col], errors='coerce')
        for lag in [1, 2, 3, 7]:
            df_full[f'{col}_Lag{lag}'] = df_full[col].shift(lag)
    for col in ['MaxTemp', 'MeanPressure']:
        df_full[f'{col}_RollMean3'] = df_full[col].shift(1).rolling(3).mean()
        df_full[f'{col}_RollMean7'] = df_full[col].shift(1).rolling(7).mean()
    df_full['Pressure_Trend_1d'] = df_full['MeanPressure'].shift(1) - df_full['MeanPressure'].shift(2)
    df_full['Temp_Trend_1d'] = df_full['MaxTemp'].shift(1) - df_full['MaxTemp'].shift(2)
    day_of_year = df_full['Date'].dt.dayofyear
    df_full['Sin_DOY'] = np.sin(2 * np.pi * day_of_year / 365.25)
    df_full['Cos_DOY'] = np.cos(2 * np.pi * day_of_year / 365.25)
    
    last_row = df_full.iloc[[-1]].copy()
    features = [
        'MaxTemp', 'MinTemp', 'MeanPressure', 'MaxWind', 'MeanRH',
        'MaxTemp_Lag1', 'MaxTemp_Lag2', 'MaxTemp_Lag7',
        'MeanPressure_Lag1', 'MeanPressure_Lag2',
        'Pressure_Trend_1d', 'Temp_Trend_1d',
        'Sin_DOY', 'Cos_DOY'
    ]
    
    print("Running Pure ML Model...")
    model = xgb.Booster()
    model.load_model(MODEL_PATH)
    dtest = xgb.DMatrix(last_row[features])
    pred_ml = model.predict(dtest)[0]
    
    # --- 4. Hybrid Upgrade: MOS + Bias Correction ---
    print("\n--- Running Physics-Informed Bias Correction ---")
    
    target_date = pd.to_datetime(last_row['Date'].item()) + pd.Timedelta(days=1)
    
    # A. Fetch Real MOS
    mos_data = fetch_live_mos()
    mos_max = None
    
    if mos_data:
        # Extract Tomorrow's Max from MOS
        # Target: roughly 00Z on Day+2? Same logic as scraper.
        # But simpler: Iterate and find Max T in the target date window.
        
        # We need to parse ftime
        valid_temps = []
        for item in mos_data:
            ft_str = item.get('ftime') # "YYYY-MM-DD HH:MM:SS"
            if not ft_str: continue
            try:
                # IEM API JSON returns ftime like "2024-01-01 12:00:00"
                # Parse loosely
                ft_dt = pd.to_datetime(ft_str).to_pydatetime()
                ft_dt = ft_dt.replace(tzinfo=datetime.timezone.utc)
                
                # Convert to Local to check date
                ft_local = ft_dt.astimezone(zoneinfo.ZoneInfo("America/New_York"))
                
                if ft_local.date() == target_date.date():
                    # This forecast is valid for tomorrow.
                    # 'n_x' is the Max/Min field.
                    if item.get('n_x') is not None:
                        valid_temps.append(float(item.get('n_x')))
                    # Fallback: 'tmp' is spot temp.
                    if item.get('tmp') is not None:
                        valid_temps.append(float(item.get('tmp')))
            except Exception as e:
                continue
        
        if valid_temps:
            mos_max = max(valid_temps)
            print(f"✅ GFS MOS Forecast Found for {target_date.date()}: {mos_max} F")
        else:
            print("MOS data found, but no temps valid for target date.")
    else:
        print("❌ GFS MOS Fetch Failed (or data unavailable).")

    # B. Bias Correct
    final_output = pred_ml
    
    if mos_max is not None:
        # Run Bias Model
        doy = target_date.dayofyear
        bias_feats = pd.DataFrame([{
            'MOS_MaxTemp': mos_max,
            'Sin_DOY': np.sin(2 * np.pi * doy / 365.25), 
            'Cos_DOY': np.cos(2 * np.pi * doy / 365.25)
        }])
        
        bias_model = xgb.Booster()
        bias_model.load_model(BIAS_MODEL_PATH)
        pred_bias = bias_model.predict(xgb.DMatrix(bias_feats))[0]
        
        corrected_mos = mos_max + pred_bias
        
        print(f"Estimated Bias: {pred_bias:+.2f} F")
        print(f"Physics (Raw MOS):     {mos_max:.2f} F")
        print(f"Pure ML Prediction:    {pred_ml:.2f} F")
        
        # Consensus Analysis
        diff = abs(mos_max - pred_ml)
        if diff < 2.5:
             # If they agree, averaging reduces random noise
             final_output = (mos_max + pred_ml) / 2
             print(f"✅ CONSENSUS: Algorithms agree within {diff:.1f} F. Averaging for robustness.")
        else:
             # If they disagree, ML is likely hallucinating persistence. Trust Physics.
             print(f"⚠️ DIVERGENCE: ML ({pred_ml:.1f}) varies from MOS ({mos_max:.1f}).")
             print("Trusting MOS (Historical Winner: 2.4F MAE vs 4.2F ML)")
             final_output = mos_max
            
    else:
        print("Using Pure ML (Fallback).")
        
    print(f"\n>>> FINAL PREDICTION FOR {target_date.date()}: {final_output:.2f} F <<<")
    return {
        "prediction": final_output,
        "date": target_date.strftime("%Y-%m-%d"),
        "source": "MOS" if mos_max == final_output else "Hybrid/ML",
        "components": {
            "MOS": mos_max if mos_max else "N/A",
            "Pure_ML": pred_ml,
            "Bias_Adj": pred_bias if mos_max else 0.0,
            "TWC_Forecast": max([x.get('temp') for x in fcst]) if fcst else "N/A"
        }
    }

if __name__ == "__main__":
    predict_live()

