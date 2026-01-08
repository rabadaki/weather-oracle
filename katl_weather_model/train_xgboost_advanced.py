import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
import sys

# Settings
INPUT_FILE = "/Users/Amos/weather-model/katl_weather_model/katl_full_history.csv"

def train_and_evaluate():
    print("Loading data...")
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found.")
        return

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)

    # --- Feature Engineering ---
    print("Engineering features...")
    
    # 1. Target: MaxTemp (We predict T+1, but let's shift target explicitly for training)
    # We want to predict 'MaxTemp' of Day D using features from D-1? 
    # Or Predict 'MaxTemp' of Day D using features known at D (Forecast)?
    # Standard: At end of Day D, we predict MaxTemp(D+1).
    # So Target = MaxTemp.shift(-1).
    
    df['Target'] = df['MaxTemp'].shift(-1)
    
    # 2. Lags
    for col in ['MaxTemp', 'MinTemp', 'MeanPressure', 'MaxWind', 'MeanRH']:
        # Ensure numeric
        df[col] = pd.to_numeric(df[col], errors='coerce')
        for lag in [1, 2, 3, 7]:
            df[f'{col}_Lag{lag}'] = df[col].shift(lag)
            
    # 3. Rolling Stats (Window 3, 7)
    for col in ['MaxTemp', 'MeanPressure']:
        df[f'{col}_RollMean3'] = df[col].shift(1).rolling(3).mean()
        df[f'{col}_RollMean7'] = df[col].shift(1).rolling(7).mean()
        
    # 4. Deltas (Trends)
    df['Pressure_Trend_1d'] = df['MeanPressure'].shift(1) - df['MeanPressure'].shift(2)
    df['Temp_Trend_1d'] = df['MaxTemp'].shift(1) - df['MaxTemp'].shift(2)
    
    # 5. Seasonality
    day_of_year = df['Date'].dt.dayofyear
    df['Sin_DOY'] = np.sin(2 * np.pi * day_of_year / 365.25)
    df['Cos_DOY'] = np.cos(2 * np.pi * day_of_year / 365.25)
    
    # 6. Interaction
    # Cold front signature: Drop in pressure then rise? Or Wind shift? 
    # If Pressure drops (neg trend) and Wind high -> storm/front?
    
    # Drop NaNs
    df_clean = df.dropna().copy()
    
    features = [c for c in df_clean.columns if c not in ['Date', 'Target'] and 'Limit' not in c]
    # Refine feature list
    features = [
        'MaxTemp', 'MinTemp', 'MeanPressure', 'MaxWind', 'MeanRH',
        'MaxTemp_Lag1', 'MaxTemp_Lag2', 'MaxTemp_Lag7',
        'MeanPressure_Lag1', 'MeanPressure_Lag2',
        'Pressure_Trend_1d', 'Temp_Trend_1d',
        'Sin_DOY', 'Cos_DOY'
    ]
    
    print(f"Features ({len(features)}): {features}")
    
    # --- Backtest: Jan 4 and Jan 5 ---
    # We want to emulate being on Jan 3 (predicting Jan 4) and Jan 4 (predicting Jan 5).
    # But wait, the user said "focus on jan 4 and 5".
    # Usually this means "Predict FOR Jan 4" and "Predict FOR Jan 5".
    
    dates_to_test = ['2026-01-04', '2026-01-05']
    
    print("\n--- Starting Backtest ---")
    
    for target_date_str in dates_to_test:
        target_date = pd.Timestamp(target_date_str)
        # We need to train on data strictly BEFORE this date's input.
        # Logic: To predict Target(D), we utilize Features(D-1).
        # In our dataframe row 'D-1' contains features for D (Target column).
        # So we split based on Date < (TargetDate - 1 Day).
        
        # Actually easier:
        # Our row at index T contains: Features(T), Target(T+1).
        # To predict T+1 (TargetDate), we use row T.
        # Training data: All rows where Date < T.
        
        pred_date_row = df_clean[df_clean['Date'] == (target_date - pd.Timedelta(days=1))]
        if pred_date_row.empty:
            print(f"Skipping {target_date_str}: Previous day data not found.")
            continue
            
        test_idx = pred_date_row.index[0]
        # Train on all previous data
        X_train = df_clean.loc[df_clean.index < test_idx, features]
        y_train = df_clean.loc[df_clean.index < test_idx, 'Target']
        
        # Test Input
        X_test = df_clean.loc[[test_idx], features]
        actual = df_clean.loc[test_idx, 'Target']
        
        print(f"\nTarget Date: {target_date_str}")
        print(f"Training on {len(X_train)} historical samples (up to {X_train.index[-1]})...")
        
        model = xgb.XGBRegressor(
            n_estimators=500,
            learning_rate=0.01,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            n_jobs=1,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        
        pred = model.predict(X_test)[0]
        
        print(f"Forecast: {pred:.2f} F")
        print(f"Actual:   {actual:.2f} F")
        print(f"Error:    {pred - actual:.2f} F")
        
    print("\n--- Final Training on Full History ---")
    # Train on EVERYTHING
    X_train_full = df_clean[features]
    y_train_full = df_clean['Target']
    
    final_model = xgb.XGBRegressor(
        n_estimators=500,
        learning_rate=0.01,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=1,
        random_state=42
    )
    final_model.fit(X_train_full, y_train_full)
    
    model_path = "/Users/Amos/weather-model/katl_weather_model/katl_xgb_model.json"
    final_model.get_booster().save_model(model_path)
    print(f"Saved final model to {model_path}")

    print("\nDone.")

if __name__ == "__main__":
    train_and_evaluate()
