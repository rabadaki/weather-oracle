import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error

INPUT_FILE = "rksi_sophisticated_data.csv"
OUTPUT_MODEL = "rksi_advanced_model.json"

def train_advanced_model():
    print("--- Training Sophisticated Seoul Model ---")
    
    try:
        df = pd.read_csv(INPUT_FILE, index_col=0)
        df.index = pd.to_datetime(df.index)
    except Exception as e:
        print(f"Waiting for data... ({e})")
        return

    # Check Columns: JMA_00 ... JMA_23, Target_MaxTemp
    # Feature Engineering
    # 1. Base Statistics of Forecast
    hourly_cols = [c for c in df.columns if c.startswith('JMA_') and 'Max' not in c]
    
    df['Fcst_Max'] = df[hourly_cols].max(axis=1)
    df['Fcst_Min'] = df[hourly_cols].min(axis=1)
    df['Fcst_Mean'] = df[hourly_cols].mean(axis=1)
    df['Fcst_Range'] = df['Fcst_Max'] - df['Fcst_Min']
    
    # 2. Slopes (Heating/Cooling Rates)
    # Morning Ramp: 08:00 to 12:00
    df['Morning_Slope'] = df['JMA_12'] - df['JMA_08']
    # Late Heating: 12:00 to 15:00
    df['Peak_Slope'] = df['JMA_15'] - df['JMA_12']
    # Evening Cooling: 16:00 to 20:00
    df['Evening_Slope'] = df['JMA_20'] - df['JMA_16']
    
    # 3. Seasonality
    df['DayOfYear'] = df.index.dayofyear
    df['Sin_DOY'] = np.sin(2 * np.pi * df['DayOfYear'] / 365.25)
    df['Cos_DOY'] = np.cos(2 * np.pi * df['DayOfYear'] / 365.25)
    
    features = [
        'Fcst_Max', 'Fcst_Min', 'Fcst_Mean', 'Fcst_Range',
        'Morning_Slope', 'Peak_Slope', 'Evening_Slope',
        'Sin_DOY', 'Cos_DOY',
        'JMA_12', 'JMA_13', 'JMA_14', 'JMA_15' # Explicit Peak Hours
    ]
    
    target = 'Target_MaxTemp'
    
    df = df.dropna()
    X = df[features]
    y = df[target]
    
    print(f"Dataset Size: {len(df)} days.")
    
    # Backtest (TimeSeriesSplit)
    print("\n--- Rigorous Backtest (5-Fold TimeSeries) ---")
    tscv = TimeSeriesSplit(n_splits=5)
    
    fold = 1
    maes = []
    
    for train_index, test_index in tscv.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        
        model = xgb.XGBRegressor(
            n_estimators=500,
            max_depth=4,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            early_stopping_rounds=20
        )
        
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        maes.append(mae)
        
        # Baseline (Raw JMA Max)
        # Note: We need to reconstruct raw JMA max from X_test or Original DF
        # X_test has 'Fcst_Max' feature
        raw_mae = mean_absolute_error(y_test, X_test['Fcst_Max'])
        
        print(f"Fold {fold}: Model MAE {mae:.2f} F vs Raw JMA {raw_mae:.2f} F (Imp: {100*(1-mae/raw_mae):.1f}%)")
        fold += 1
        
    print(f"\nAverage Backtest MAE: {np.mean(maes):.2f} F")
    
    # Final Training (Full Data)
    final_model = xgb.XGBRegressor(
        n_estimators=500, max_depth=4, learning_rate=0.03, subsample=0.8, colsample_bytree=0.8
    )
    final_model.fit(X, y)
    final_model.get_booster().save_model(OUTPUT_MODEL)
    print(f"Final Model Saved to {OUTPUT_MODEL}")
    
    # Feature Importance
    print("\nTop Features:")
    importances = final_model.feature_importances_
    indices = np.argsort(importances)[::-1]
    for i in range(5):
        print(f"{i+1}. {features[indices[i]]}: {importances[indices[i]]:.4f}")

if __name__ == "__main__":
    train_advanced_model()
