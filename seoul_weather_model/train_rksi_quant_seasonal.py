import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

INPUT_FILE = "/Users/Amos/seoul_weather_model/rksi_daily.csv"

def train_quant_seasonal(window_days=30):
    print(f"Loading data... (Feature Engineering + Seasonal Window ±{window_days}d)")
    try:
        df = pd.read_csv(INPUT_FILE)
    except: return

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    # --- 1. Quant Feature Engineering (Global) ---
    # Must do this BEFORE filtering to preserve rolling stats
    
    # Derivatives
    df['Delta_MaxTemp'] = df['MaxTemp'].diff()
    df['Delta_MinTemp'] = df['MinTemp'].diff()
    df['Delta_Pressure'] = df['MeanPressure'].diff()
    
    # Diurnal & Volatility
    df['Diurnal_Range'] = df['MaxTemp'] - df['MinTemp']
    df['Vol_MaxTemp_3d'] = df['MaxTemp'].rolling(window=3).std()
    
    # EMAs (Momentum)
    df['EMA_Max_3'] = df['MaxTemp'].ewm(span=3).mean()
    df['EMA_Max_7'] = df['MaxTemp'].ewm(span=7).mean()
    df['Trend_Strength'] = df['EMA_Max_3'] - df['EMA_Max_7']
    
    # Target: Tomorrow's Max
    df['Target'] = df['MaxTemp'].shift(-1)
    
    # Lags of Quant Features
    quant_cols = ['Delta_MaxTemp', 'Delta_Pressure', 'Diurnal_Range', 'Trend_Strength']
    for col in quant_cols:
        df[f'{col}_Lag1'] = df[col].shift(1)
        
    # Seasonality
    doy = df['Date'].dt.dayofyear
    df['Sin_DOY'] = np.sin(2 * np.pi * doy / 365.25)
    df['Cos_DOY'] = np.cos(2 * np.pi * doy / 365.25)

    df_clean = df.dropna()
    drop_cols = ['Date', 'Target']
    features = [c for c in df_clean.columns if c not in drop_cols]
    
    # --- 2. Seasonal Window Training Loop ---
    
    test_mask = df_clean['Date'].dt.year == 2025
    test_indices = df_clean[test_mask].index
    
    predictions = []
    actuals = []
    
    print(f"Running Quant + Seasonal training for {len(test_indices)} days in 2025...")
    
    count = 0
    for idx in test_indices:
        target_date = df_clean.loc[idx, 'Date']
        target_doy = target_date.dayofyear
        
        # History: All dates BEFORE target
        history = df_clean[df_clean['Date'] < target_date]
        
        # Seasonal Filter
        history_doy = history['Date'].dt.dayofyear
        diff = np.abs(history_doy - target_doy)
        diff = np.minimum(diff, 365 - diff)
        
        train_subset = history[diff <= window_days]
        
        if len(train_subset) < 50:
            train_subset = history # Fallback
            
        X_train = train_subset[features]
        y_train = train_subset['Target']
        
        X_test = df_clean.loc[[idx], features]
        y_test_val = df_clean.loc[idx, 'Target']
        
        # Model (Quant params)
        model = xgb.XGBRegressor(
            n_estimators=100, 
            max_depth=4, 
            learning_rate=0.05, 
            n_jobs=1
        )
        model.fit(X_train, y_train)
        
        pred = model.predict(X_test)[0]
        predictions.append(pred)
        actuals.append(y_test_val)
        
        count += 1
        if count % 50 == 0: print(f"Processed {count} days...")
        
    mae = mean_absolute_error(actuals, predictions)
    print(f"\n--- Quant + Seasonal Result ---")
    print(f"MAE: {mae:.2f} F")

if __name__ == "__main__":
    train_quant_seasonal()
