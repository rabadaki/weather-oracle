import pandas as pd
import xgboost as xgb
import numpy as np
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit

# Files
HISTORY_FILE = "katl_weather_model/katl_full_history.csv"
MOS_FILE = "katl_weather_model/katl_mos_history.csv"

def backtest_hybrid():
    print("--- Backtesting Hybrid Strategy (ML + MOS) [2015-2025] ---")
    
    # 1. Load Data
    df = pd.read_csv(HISTORY_FILE)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
    mos = pd.read_csv(MOS_FILE)
    mos['Date'] = pd.to_datetime(mos['Date'])
    
    # Merge MOS into history (Lossy merge - only days where we have both)
    df = pd.merge(df, mos, on='Date', how='inner')
    print(f"Total Aligned Data Points: {len(df)}")
    
    # 2. Feature Engineering (Simplified from main script for speed)
    # Lags
    for col in ['MaxTemp', 'MinTemp', 'MeanPressure', 'MaxWind', 'MeanRH']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        for lag in [1, 2, 3, 7]:
            df[f'{col}_Lag{lag}'] = df[col].shift(lag)
            
    # Seasonality
    doy = df['Date'].dt.dayofyear
    df['Sin_DOY'] = np.sin(2 * np.pi * doy / 365.25)
    df['Cos_DOY'] = np.cos(2 * np.pi * doy / 365.25)
    
    # Target: Next Day MaxTemp
    df['Target'] = df['MaxTemp'].shift(-1)
    
    # MOS alignment is tricky here. 
    # The 'MOS_MaxTemp' column in mos_history is ALREADY aligned to the forecast date.
    # So if df row is Jan 1, Target is Jan 2 Max.
    # We need MOS for Jan 2 to compare.
    # So we shift MOS backwards? No.
    # We want to predict Target(t+1).
    # We have MOS(t+1) available at time t? 
    # Yes, the scraper aligned 'Date' to the *Validity Time*.
    # So df['MOS_MaxTemp'] at row Jan 2 IS the forecast for Jan 2.
    # But we are predicting Jan 2 FROM Jan 1 data.
    # So at row Jan 1 (Features), we need MOS(Jan 2).
    # So we need to SHIFT MOS BACK by 1 to be a feature/comparator for row Jan 1.
    
    df['MOS_Target'] = df['MOS_MaxTemp'].shift(-1)
    
    # Drop NaNs
    df.dropna(inplace=True)
    
    features = [
        'MaxTemp', 'MinTemp', 'MeanPressure', 'MaxWind', 'MeanRH',
        'MaxTemp_Lag1', 'MaxTemp_Lag2', 'MaxTemp_Lag7',
        'Sin_DOY', 'Cos_DOY'
    ]
    
    X = df[features]
    y = df['Target']
    y_mos = df['MOS_Target'] # The rival prediction
    
    # 3. Time Series Cross Validation
    tscv = TimeSeriesSplit(n_splits=5)
    
    mae_ml = []
    mae_mos = []
    mae_hybrid = []
    
    print("\n[Running Cross-Validation]")
    for i, (train_index, test_index) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        mos_test = y_mos.iloc[test_index]
        
        # Train ML
        model = xgb.XGBRegressor(n_estimators=500, max_depth=5, learning_rate=0.01, n_jobs=4)
        model.fit(X_train, y_train)
        
        # Predict
        pred_ml = model.predict(X_test)
        
        # Evaluate
        err_ml = mean_absolute_error(y_test, pred_ml)
        err_mos = mean_absolute_error(y_test, mos_test)
        
        # Hybrid
        pred_hybrid = (pred_ml + mos_test) / 2
        err_hybrid = mean_absolute_error(y_test, pred_hybrid)
        
        mae_ml.append(err_ml)
        mae_mos.append(err_mos)
        mae_hybrid.append(err_hybrid)
        
        print(f"Fold {i+1}: ML={err_ml:.2f} | MOS={err_mos:.2f} | Hybrid={err_hybrid:.2f}")

    print("\n--- Final Results ---")
    print(f"Average MAE (Pure ML): {np.mean(mae_ml):.3f} F")
    print(f"Average MAE (Raw MOS): {np.mean(mae_mos):.3f} F")
    print(f"Average MAE (Hybrid):  {np.mean(mae_hybrid):.3f} F")
    
    best = np.argmin([np.mean(mae_ml), np.mean(mae_mos), np.mean(mae_hybrid)])
    names = ["Pure ML", "Raw MOS", "Hybrid"]
    print(f"\nWINNER: {names[best]}")

if __name__ == "__main__":
    backtest_hybrid()
