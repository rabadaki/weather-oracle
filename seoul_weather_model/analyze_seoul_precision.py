import pandas as pd
import numpy as np

INPUT_FILE = "/Users/Amos/seoul_weather_model/rksi_hourly.csv"

def analyze_seoul_precision():
    try:
        df = pd.read_csv(INPUT_FILE)
    except: return

    df['Date'] = pd.to_datetime(df['Date'])
    df['Temp'] = pd.to_numeric(df['Temp'], errors='coerce')
    df = df.dropna(subset=['Temp'])
    
    daily_groups = df.groupby('Date')
    data = []
    
    for date, group in daily_groups:
        try:
            max_val = group['Temp'].max()
            
            # Temp at 12:00 PM
            row_12 = group[group['Hour'] == 12]
            if row_12.empty: continue
            
            t_12 = row_12['Temp'].mean()
            
            diff = max_val - t_12
            
            data.append({
                'Date': date,
                'Max': max_val,
                'T_12': t_12,
                'Diff': diff
            })
        except: continue
        
    res = pd.DataFrame(data)
    
    print("\n--- Seoul Intraday Precision (12:00 PM KST) ---")
    print(f"Sample Size: {len(res)} days")
    
    # Metrics
    # How often is T_12 within 1 degree of Max?
    within_1 = np.mean(res['Diff'] <= 1.0) * 100
    within_0 = np.mean(res['Diff'] == 0) * 100
    
    avg_warming = res['Diff'].mean()
    
    print(f"Average Warming after 12:00 PM: {avg_warming:.2f} F")
    print(f"Chance Max is within 1°F of 12 PM Temp: {within_1:.1f}%")
    print(f"Chance 12 PM Temp IS the Max (0°F rise): {within_0:.1f}%")
    
    # Linear Regression Model
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error
    
    X = res[['T_12']].values
    y = res['Max'].values
    
    lr = LinearRegression()
    lr.fit(X, y)
    preds = lr.predict(X)
    
    mae = mean_absolute_error(y, preds)
    r2 = lr.score(X, y)
    
    print(f"\n--- Model Prediction (Correcting for Warming) ---")
    print(f"Regression Equation: Max ≈ {lr.coef_[0]:.2f} * T_12 + {lr.intercept_:.2f}")
    print(f"R-Squared: {r2:.4f}")
    print(f"Model MAE: {mae:.2f} F")
    
    # Hit Rate of Model
    errors = np.abs(y - preds)
    hit_1f = np.mean(errors <= 1.0) * 100
    
    print(f"Win Rate (Model within ±1°F): {hit_1f:.1f}%")

    # Conclusion
    print("\n--- Strategy Implication ---")
    if hit_1f > 55:
        print("SAFE BET: With the Model correction, you have a winning edge (>55%).")
    else:
        print(f"RISKY: Even with a model, the volatility is too high (Win Rate {hit_1f:.1f}%).")

if __name__ == "__main__":
    analyze_seoul_precision()
