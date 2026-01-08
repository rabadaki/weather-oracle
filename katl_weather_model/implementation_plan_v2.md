# Implementation Plan: Atlanta Upgrade & Continuous Learning

## Goal 1: The "Atlanta Challenge" (Advanced ML vs MOS)
We proved "Hourly Features" worked for Seoul. Now we test them for Atlanta.
*   **Hypothesis**: Can an XGBoost model using "Heating Slopes" (Hourly GFS) beat the NWS MOS (2.4 F MAE)?
*   **Data Source**: Open-Meteo GFS (Hourly) for KATL (2020-2025).
*   **Target**: TWC Actuals.
*   **Comparison**: 
    1.  Fetch 5 Years of Hourly GFS for Atlanta.
    2.  Train "Seoul-Style" Advanced Model.
    3.  Compare its MAE vs the known 2.4 F MOS benchmark.
    4.  If it wins, we switch Atlanta to the "Seoul Strategy".

## Goal 2: Continuous Data Pipeline
Stop relying on "Bulk Backfills". Create a script that runs Daily.
*   **Script**: `run_daily_ops.py`
*   **Functions**:
    1.  **Prediction**: Runs `predict_live.py` (Atlanta) and `predict_seoul.py` (Seoul).
    2.  **Logging**: Appends the prediction to `predictions_log.csv`.
    3.  **Ground Truth**: Fetches *Yesterday's* Actuals (TWC) and appends to `history_log.csv`.
    4.  **Auto-Retrain**: (Optional) Triggers retraining if error spikes.

## Execution Order
1.  **Fetch KATL Hourly Data** (via Open-Meteo).
2.  **Train & Benchmark** (Advanced ML vs MOS).
3.  **Build `run_daily_ops.py`**.
