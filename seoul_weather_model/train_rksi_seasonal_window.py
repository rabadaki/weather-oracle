import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
from datetime import timedelta

INPUT_FILE = "/Users/Amos/seoul_weather_model/rksi_daily.csv"

def train_seasonal_window(window_days=30):
    print(f"Loading data... (Seasonal Window = ±{window_days} days)")
    try:
        df = pd.read_csv(INPUT_FILE)
    except: 
        print("File not found.")
        return

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Target: Tomorrow's Max (Day-1 Forecast)
    df['Target'] = df['MaxTemp'].shift(-1)
    
    # Features (Same as before)
    for col in ['MaxTemp', 'MinTemp', 'MeanPressure']:
        for lag in [1, 2, 3]:
            df[f'{col}_Lag{lag}'] = df[col].shift(lag)
            
    df_clean = df.dropna()
    
    features = ['MaxTemp', 'MinTemp', 'MeanPressure', 'MaxWind', 'MeanRH'] + \
               [c for c in df_clean.columns if 'Lag' in c]
    if 'Target' in features: features.remove('Target')
    
    # Test Set: 2025
    test_mask = df_clean['Date'].dt.year == 2025
    test_indices = df_clean[test_mask].index
    
    predictions = []
    actuals = []
    
    print(f"Running rolling seasonal training for {len(test_indices)} days in 2025...")
    
    count = 0
    for idx in test_indices:
        target_date = df_clean.loc[idx, 'Date']
        target_doy = target_date.dayofyear
        
        # Training Set: All dates BEFORE target_date where DOY is within window
        # Logic: abs(DOY - TargetDOY) <= window
        # Handle year wrap-around (e.g. Jan 1 vs Dec 31)
        
        # We look at history (2015-2024)
        history = df_clean[df_clean['Date'] < target_date]
        
        # Calculate DoY difference handling wrap for 365 days
        history_doy = history['Date'].dt.dayofyear
        
        # Distance function
        diff = np.abs(history_doy - target_doy)
        diff = np.minimum(diff, 365 - diff) # Wrap around distance
        
        # Filter
        train_subset = history[diff <= window_days]
        
        if len(train_subset) < 50:
            # Fallback if somehow not enough data
            print(f"Warning: Low data for {target_date}")
            train_subset = history 
            
        X_train = train_subset[features]
        y_train = train_subset['Target']
        
        X_test = df_clean.loc[[idx], features]
        y_test_val = df_clean.loc[idx, 'Target']
        
        # Train specialized model
        model = xgb.XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, n_jobs=1)
        model.fit(X_train, y_train)
        
        pred = model.predict(X_test)[0]
        predictions.append(pred)
        actuals.append(y_test_val)
        
        count += 1
        if count % 50 == 0:
            print(f"Processed {count} days...")
            
    # Evaluation
    mae = mean_absolute_error(actuals, predictions)
    print(f"\n--- Seasonal Window Results (±{window_days} Days) ---")
    print(f"MAE: {mae:.2f} F")
    
    # Baseline comparison (Full History Model was 3.85 F)
    # Persistence
    persist_preds = df_clean.loc[test_indices, 'MaxTemp'].values # Today's Max
    p_mae = mean_absolute_error(actuals, persist_preds)
    print(f"Persistence MAE: {p_mae:.2f} F")

if __name__ == "__main__":
    train_seasonal_window(window_days=30)
