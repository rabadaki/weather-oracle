import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

INPUT_FILE = "/Users/Amos/seoul_weather_model/rksi_daily.csv"

def train_quant_model():
    print("Loading daily data...")
    try:
        df = pd.read_csv(INPUT_FILE)
    except Exception as e:
        print(f"Error: {e}")
        return

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    # --- Quant Feature Engineering ---
    
    # 1. Physics / Derivatives
    # Velocity: How fast is Temp changing day-over-day?
    df['Delta_MaxTemp'] = df['MaxTemp'].diff()
    df['Delta_MinTemp'] = df['MinTemp'].diff()
    df['Delta_Pressure'] = df['MeanPressure'].diff()
    
    # Acceleration: Is the warming/cooling speeding up?
    df['Accel_MaxTemp'] = df['Delta_MaxTemp'].diff()
    df['Accel_Pressure'] = df['Delta_Pressure'].diff()
    
    # 2. Structural / Regime Features
    # Diurnal Range: (Max - Min). Large range = Clear/Stable. Small range = Cloudy/Isobaric.
    df['Diurnal_Range'] = df['MaxTemp'] - df['MinTemp']
    
    # Volatility (Rolling Std Dev of MaxTemp) - Regime detection
    # If volatility is high, we are in a transition period (harder to predict).
    df['Vol_MaxTemp_3d'] = df['MaxTemp'].rolling(window=3).std()
    
    # 3. Trends / Momentum (EMA)
    # Is the trend upwards or downwards short-term vs long-term?
    df['EMA_Max_3'] = df['MaxTemp'].ewm(span=3).mean()
    df['EMA_Max_7'] = df['MaxTemp'].ewm(span=7).mean()
    df['Trend_Strength'] = df['EMA_Max_3'] - df['EMA_Max_7'] # Signal Line
    
    # 4. Interaction Terms (Thermodynamics proxies)
    # Pressure * Change in Pressure (Frontal strength?)
    # df['Pressure_Momentum'] = df['MeanPressure'] * df['Delta_Pressure'] 
    
    # --- Standard Shifts for Prediction ---
    # We are predicting Tomorrow (D+1).
    # All features must be known Today (D).
    # So we take the features calculated above (which exist at row D) and use them.
    # We simply need to shift the TARGET back by 1 (or feat forward? No).
    # Row D: Features(D). Target = MaxTemp(D+1).
    
    df['Target'] = df['MaxTemp'].shift(-1)
    
    # Lags of the *New* Quant Features
    # Does yesterday's acceleration predict tomorrow's max? Maybe.
    # Let's add Lag1 of key quant metrics.
    quant_cols = ['Delta_MaxTemp', 'Delta_Pressure', 'Diurnal_Range', 'Trend_Strength']
    for col in quant_cols:
        df[f'{col}_Lag1'] = df[col].shift(1)
        
    # Seasonality (Standard)
    doy = df['Date'].dt.dayofyear
    df['Sin_DOY'] = np.sin(2 * np.pi * doy / 365.25)
    df['Cos_DOY'] = np.cos(2 * np.pi * doy / 365.25)

    # --- Data Prep ---
    df_clean = df.dropna()
    
    # Feature Selection
    # Drop "Target" and "Date"
    drop_cols = ['Date', 'Target']
    features = [c for c in df_clean.columns if c not in drop_cols]
    
    print(f"Engineered {len(features)} Quant features.")
    
    # Train/Test Split (2015-2024 to Train, 2025 to Test)
    test_start_date = pd.to_datetime("2025-01-01")
    
    train = df_clean[df_clean['Date'] < test_start_date]
    test = df_clean[df_clean['Date'] >= test_start_date]
    
    X_train = train[features]
    y_train = train['Target']
    X_test = test[features]
    y_test = test['Target']
    
    print(f"Training on {len(train)} days (2015-2024), Testing on {len(test)} days (2025)...")
    
    # Model
    model = xgb.XGBRegressor(
        n_estimators=1000, 
        max_depth=4, 
        learning_rate=0.02, 
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=1,
        early_stopping_rounds=50
    )
    
    # Use a chunk of train as validation for early stopping? 
    # Or just fit. Let's fit.
    # Actually, XGBoost requires eval_set for early_stopping.
    # We'll split Train into Train/Val.
    
    val_size = int(len(train) * 0.1)
    train_part = train.iloc[:-val_size]
    val_part = train.iloc[-val_size:]
    
    model.fit(
        train_part[features], train_part['Target'],
        eval_set=[(val_part[features], val_part['Target'])],
        verbose=False
    )
    
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    
    print(f"\n--- Seoul Quant Model Results ---")
    print(f"MAE: {mae:.2f} F")
    
    # Feature Importance
    print("\n--- Top 10 Features (Gain) ---")
    importance = model.feature_importances_
    feat_imp = pd.DataFrame({'Feature': features, 'Importance': importance})
    feat_imp = feat_imp.sort_values('Importance', ascending=False).head(10)
    print(feat_imp)
    
    # Baseline Check
    persist_mae = mean_absolute_error(y_test, test['MaxTemp']) # Today's max as pred
    print(f"\nPersistence MAE: {persist_mae:.2f} F")
    print(f"Improvement: {(1 - mae/persist_mae)*100:.1f}%")

if __name__ == "__main__":
    train_quant_model()
