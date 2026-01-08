import pandas as pd
import xgboost as xgb
import numpy as np
from sklearn.metrics import mean_absolute_error

# Files
# Files
MOS_FILE = "katl_weather_model/katl_mos_history.csv"
ACTUALS_FILE = "katl_weather_model/katl_full_history.csv"
OUTPUT_MODEL = "katl_weather_model/katl_bias_model.json"

def train_bias_corrector():
    print("Loading data...")
    mos = pd.read_csv(MOS_FILE)
    actuals = pd.read_csv(ACTUALS_FILE)
    
    # Merge on Date
    df = pd.merge(mos, actuals, on="Date")
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Target: The Bias (Error)
    # Bias = Actual - MOS
    # If MOS says 50, Actual is 55, Bias is +5.
    df['Bias'] = df['MaxTemp'] - df['MOS_MaxTemp']
    
    print(f"Average Bias: {df['Bias'].mean():.2f} F")
    
    # Features for the Corrector
    # We want to know: "When does MOS get it wrong?"
    # It gets it wrong based on:
    # 1. Seasonality (Time of year)
    # 2. The Forecasted Value itself (maybe it struggles with specific temps)
    # 3. Recent Actuals (if we are in a heatwave, MOS might lag)
    
    df['DayOfYear'] = df['Date'].dt.dayofyear
    df['Sin_DOY'] = np.sin(2 * np.pi * df['DayOfYear'] / 365.25)
    df['Cos_DOY'] = np.cos(2 * np.pi * df['DayOfYear'] / 365.25)
    
    features = ['MOS_MaxTemp', 'Sin_DOY', 'Cos_DOY']
    # If we had Pressure/Wind in the MOS file, we'd add them here.
    
    # Split
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
    
    # Eliminate Bias?
    pred_bias = model.predict(X_test)
    
    # Final Prediction = MOS + Predicted_Bias
    final_pred = test['MOS_MaxTemp'] + pred_bias
    
    # Metrics
    # 1. Raw MOS Performance
    mae_mos = mean_absolute_error(test['MaxTemp'], test['MOS_MaxTemp'])
    print(f"Raw MOS MAE: {mae_mos:.2f} F")
    
    # 2. Corrected Performance
    mae_corrected = mean_absolute_error(test['MaxTemp'], final_pred)
    print(f"Corrected MAE: {mae_corrected:.2f} F")
    
    improvement = (1 - mae_corrected/mae_mos) * 100
    print(f"Improvement: {improvement:.1f}%")
    
    # Save
    model.get_booster().save_model(OUTPUT_MODEL)
    print(f"Saved Bias Model to {OUTPUT_MODEL}")

if __name__ == "__main__":
    train_bias_corrector()
