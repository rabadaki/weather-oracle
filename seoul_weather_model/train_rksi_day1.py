import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

INPUT_FILE = "/Users/Amos/seoul_weather_model/rksi_daily.csv"

def train_day1_model():
    print("Loading daily data...")
    try:
        df = pd.read_csv(INPUT_FILE)
    except Exception as e:
        print(f"Error: {e}")
        return

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Target: Tomorrow's High (Day D+1)
    # Features from Day D (Today) include MaxTemp (Today).
    # We want to use features at row i to predict target at row i.
    # If row i is Day D, features are Day D stats. Target should be Day D+1 Max.
    # So Target = MaxTemp.shift(-1).
    
    df['Target'] = df['MaxTemp'].shift(-1)
    
    # Features
    # We do NOT want "Lag1" of MaxTemp if "MaxTemp" is already in the row.
    # The row contains "MaxTemp" (Today).
    # "MaxTemp_Lag1" would be Yesterday.
    # We should use Today's MaxTemp as a feature.
    
    # Let's rename columns to be clear:
    # Feature: MaxTemp_Today, MaxTemp_Yesterday (Lag1)...
    
    # Actually, let's just use the columns we have:
    # MaxTemp is Today.
    # MinTemp is Today.
    # We can use these to predict Target (Tomorrow).
    
    for col in ['MaxTemp', 'MinTemp', 'MeanPressure']:
        for lag in [1, 2, 3]:
            df[f'{col}_Lag{lag}'] = df[col].shift(lag)
            
    # Include 'MaxTemp' (Today) in features!
    # The previous script rejected it because I filtered for 'Lag'.
    
    features = ['MaxTemp', 'MinTemp', 'MeanPressure', 'MaxWind', 'MeanRH'] + \
               [c for c in df.columns if 'Lag' in c or 'DOY' in c]
    
    # Remove Target from features if it got in there (it shouldn't)
    if 'Target' in features: features.remove('Target')
    
    # Drop NAs created by lags/shifting
    df_clean = df.dropna()
    
    # Train/Test Split (Specific: Train 2015-2024, Test 2025)
    # We want to verify performance on 2025 data specifically.
    
    test_start_date = pd.to_datetime("2025-01-01")
    
    train = df_clean[df_clean['Date'] < test_start_date]
    test = df_clean[df_clean['Date'] >= test_start_date]
    
    X_train = train[features]
    y_train = train['Target']
    X_test = test[features]
    y_test = test['Target']
    
    # Revert to XGBoost (Now that we have data)
    import xgboost as xgb
    
    print(f"Training on {len(train)} days (2015-2024), Testing on {len(test)} days (2025)...")
    
    model = xgb.XGBRegressor(n_estimators=500, max_depth=3, learning_rate=0.05, n_jobs=1)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    
    print(f"\n--- Seoul Day-1 Model Results (XGBoost 10-Year) ---")
    print(f"MAE: {mae:.2f} F")
    
    # Compare to Persistence (Tomorrow = Today)
    persist_mae = mean_absolute_error(y_test, test['MaxTemp_Lag1']) # Lag1 is "Today's Max" relative to Target? No.
    # Feature Lag1 is Row[D].shift(1) -> MaxTemp[D-1].
    # Target is MaxTemp[D+1].
    # We want Persistence: Prediction = MaxTemp[D] (Today).
    # In row D, 'MaxTemp' is Today.
    persist_mae = mean_absolute_error(y_test, test['MaxTemp'])
    
    print(f"Persistence MAE: {persist_mae:.2f} F")
    print(f"Improvement: { (1 - mae/persist_mae)*100:.1f}%")

if __name__ == "__main__":
    train_day1_model()
