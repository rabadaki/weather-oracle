import pandas as pd
import xgboost as xgb
import numpy as np
from sklearn.metrics import mean_absolute_error

# Files
INPUT_FILE = "rksi_jma_training.csv"
OUTPUT_MODEL = "rksi_jma_bias_model.json"

def train_bias_corrector():
    print("Loading data...")
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"File {INPUT_FILE} not found.")
        return
        
    # The file already has merged columns: Date, MOS_MaxTemp, MaxTemp, Bias
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Filter valid
    df['MOS_MaxTemp'] = pd.to_numeric(df['MOS_MaxTemp'], errors='coerce')
    df['MaxTemp'] = pd.to_numeric(df['MaxTemp'], errors='coerce')
    df.dropna(subset=['MOS_MaxTemp', 'MaxTemp'], inplace=True)
    
    # Recalculate Bias just in case
    df['Bias'] = df['MaxTemp'] - df['MOS_MaxTemp']
    
    print(f"Average Bias (Overall): {df['Bias'].mean():.2f} F")
    
    # Features for the Corrector
    df['DayOfYear'] = df['Date'].dt.dayofyear
    df['Sin_DOY'] = np.sin(2 * np.pi * df['DayOfYear'] / 365.25)
    df['Cos_DOY'] = np.cos(2 * np.pi * df['DayOfYear'] / 365.25)
    
    features = ['MOS_MaxTemp', 'Sin_DOY', 'Cos_DOY']
    
    # Split (Backtest on last year: 2025 data, roughly 365 days)
    # Total ~1800 days.
    train = df.iloc[:-365]
    test = df.iloc[-365:]
    
    X_train = train[features]
    y_train = train['Bias']
    X_test = test[features]
    y_test = test['Bias']
    
    # Train XGBoost
    model = xgb.XGBRegressor(
        n_estimators=200, max_depth=3, learning_rate=0.05
    )
    model.fit(X_train, y_train)
    
    # Eliminate Bias
    pred_bias = model.predict(X_test)
    
    # Final Prediction = MOS + Predicted_Bias
    final_pred = test['MOS_MaxTemp'] + pred_bias
    
    # Metrics
    # 1. Raw MOS Performance
    mae_mos = mean_absolute_error(test['MaxTemp'], test['MOS_MaxTemp'])
    print(f"Raw MOS MAE: {mae_mos:.2f} F (The 'Terrible' Base)")
    
    # 2. Corrected Performance
    mae_corrected = mean_absolute_error(test['MaxTemp'], final_pred)
    print(f"Corrected MAE: {mae_corrected:.2f} F (The 'Hybrid' Result)")
    
    improvement = (1 - mae_corrected/mae_mos) * 100
    print(f"Improvement: {improvement:.1f}%")
    
    # Save
    model.get_booster().save_model(OUTPUT_MODEL)
    print(f"Saved Bias Model to {OUTPUT_MODEL}")

if __name__ == "__main__":
    train_bias_corrector()
