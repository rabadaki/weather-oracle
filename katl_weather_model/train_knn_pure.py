import csv
import math
import statistics
import os

# Settings
INPUT_FILE = "katl_features.csv"

def load_data():
    data = []
    with open(INPUT_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed_row = {}
            for k, v in row.items():
                if k == "Date":
                    parsed_row[k] = v
                else:
                    try:
                        if v == "" or v is None:
                            parsed_row[k] = None
                        else:
                            parsed_row[k] = float(v)
                    except:
                        parsed_row[k] = None
            data.append(parsed_row)
    return data

def train_predict_knn():
    data = load_data()
    print(f"Loaded {len(data)} raw rows.")
    
    # Feature Selection
    features = [
        'MaxTemp', 'MinTemp', 'Lag1', 'Lag2', 
        'Pressure_Lag1', 'Pressure_Trend', 
        'DayOfYear_Sin', 'DayOfYear_Cos'
    ]
    
    # Check validity
    # We also need Target_T1 to calculate Delta (Target - MaxTemp)
    valid_data = [d for d in data if d['Target_T1'] is not None and all(d.get(f) is not None for f in features)]
    print(f"Total Valid Samples: {len(valid_data)}")
    
    # Calculate Delta Target
    for row in valid_data:
        row['_target_delta'] = row['Target_T1'] - row['MaxTemp']
        
    # Normalize Data
    mins = {f: 10000.0 for f in features}
    maxs = {f: -10000.0 for f in features}
    
    for row in valid_data:
        for f in features:
            val = row[f]
            if val < mins[f]: mins[f] = val
            if val > maxs[f]: maxs[f] = val
            
    def get_norm_vector(row):
        # Weights
        weights = {
            'MaxTemp': 1.0, 'MinTemp': 1.0, 
            'Lag1': 1.5, 'Lag2': 1.0,
            'Pressure_Lag1': 1.0, 'Pressure_Trend': 4.0, # High weight for Pressure Trend
            'DayOfYear_Sin': 1.5, 'DayOfYear_Cos': 1.5   # seasonality matches are good
        }
        
        vec = []
        for f in features:
            denom = maxs[f] - mins[f]
            if denom == 0: denom = 1.0
            val = (row[f] - mins[f]) / denom
            val *= weights.get(f, 1.0)
            vec.append(val)
        return vec

    # Pre-calculate
    for row in valid_data:
        row['_norm_vec'] = get_norm_vector(row)

    def predict_delta_knn(test_row, history, k=25):
        test_vec = test_row['_norm_vec']
        distances = []
        for h_row in history:
            h_vec = h_row['_norm_vec']
            dist_sq = sum((a - b)**2 for a, b in zip(test_vec, h_vec))
            dist = math.sqrt(dist_sq)
            distances.append((dist, h_row))
            
        distances.sort(key=lambda x: x[0])
        neighbors = distances[:k]
        
        total_weight = 0.0
        weighted_delta = 0.0
        
        for dist, n_row in neighbors:
            weight = 1.0 / (dist + 1e-4)
            weighted_delta += n_row['_target_delta'] * weight
            total_weight += weight
            
        return weighted_delta / total_weight

    # --- Jan 5 Backtest ---
    cutoff_date = "2026-01-04"
    train_jan5 = [d for d in valid_data if d['Date'] < cutoff_date]
    test_jan5_row = next((d for d in valid_data if d['Date'] == cutoff_date), None)
    
    if test_jan5_row:
        pred_delta = predict_delta_knn(test_jan5_row, train_jan5, k=20)
        final_pred = test_jan5_row['MaxTemp'] + pred_delta
        actual = test_jan5_row['Target_T1']
        
        print(f"\n--- Prediction for Jan 5 2026 (Warm Spike) ---")
        print(f"Inputs Date: {test_jan5_row['Date']}")
        print(f"KNN Delta Forecast: {pred_delta:.2f} F")
        print(f"Final Forecast:     {final_pred:.1f} F")
        print(f"Actual:             {actual} F")
        print(f"Error:              {abs(final_pred - actual):.1f} F")

    # --- Jan 6 Backtest ---
    cutoff_date_2 = "2026-01-05"
    train_jan6 = [d for d in valid_data if d['Date'] < cutoff_date_2]
    test_jan6_row = next((d for d in valid_data if d['Date'] == cutoff_date_2), None)
    
    if test_jan6_row:
        pred_delta = predict_delta_knn(test_jan6_row, train_jan6, k=20)
        final_pred = test_jan6_row['MaxTemp'] + pred_delta
        actual = test_jan6_row['Target_T1']
        
        print(f"\n--- Prediction for Jan 6 2026 (Cold Front) ---")
        print(f"Inputs Date: {test_jan6_row['Date']}")
        print(f"KNN Delta Forecast: {pred_delta:.2f} F")
        print(f"Final Forecast:     {final_pred:.1f} F")
        print(f"Actual:             {actual} F")
        print(f"Error:              {abs(final_pred - actual):.1f} F")

if __name__ == "__main__":
    train_predict_knn()
