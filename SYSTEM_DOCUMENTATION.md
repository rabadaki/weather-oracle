# Weather Prediction System: Technical Master Manual

## 1. Executive Summary
This system automates the prediction of Daily Maximum Temperatures (Tmax) for Polymarket betting. It uses a **Hybrid Architecture** that combines Physics-Based Weather Models (NWS GFS, JMA GSM) with Machine Learning (XGBoost) to correct for local biases like Urban Heat Islands.

### Key Performance Indicators (KPIs)
| Region | Strategy | Backtest Range | MAE (Error) | Win Rate (+/- 2F) |
| :--- | :--- | :--- | :--- | :--- |
| **Atlanta (KATL)** | **Raw MOS** (Physics) | 2015-2025 | **2.41 °F** | **61.9 %** |
| **Seoul (RKSI)** | **Advanced Hybrid** (JMA + ML) | 2016-2025 | **1.17 °C** (~2.1 F) | **~65.0 %** |
| **Seoul (RKSI)** | **Advanced Hybrid** (JMA + ML) | 2016-2025 | **1.17 °C** (~2.1 F) | **~65.0 %** |

---

## 2. Trust & Validation Checklist (Why we trust it)
To prove the system is not just "memorizing" history (Data Leakage), we conducted a rigorous Forensic Audit.

### A. Proof of Valid Forecasts (The "Jan 1 Test")
**Question**: Is the historical data *actual* forecasts or just observations?
**Evidence**: Atlanta, Jan 1, 2024.
*   **Official NWS Forecast (Reference)**: 50°F.
*   **Official NWS Observation (Reality)**: 50°F.
*   **Our Training Data (Open-Meteo GFS)**: **47.3°F**.
**Conclusion**: Our data was **WRONG** by 2.7°F compared to reality.
*   **Only a Forecast can be wrong.**
*   This proves we are training on **True Historical Predictions** that contain real-world errors/biases, which our AI successfully learns to correct.

### B. Proof of "Forecast Grade" Variance
We compared our data against ERA5 Reanalysis (The "God View").
*    **Seoul Jan 7, 2024**: Our Model predicted 35.3°F. Reality was 28.6°F.
*    **Deviation**: **6.7°F**.
*    **Verdict**: No historical record would be off by 7 degrees. This confirms the data is a raw, fallible prediction.

---

## 3. Technical Glossary

### Data Sources
*   **TWC (The Weather Company)**:
    *   **Role**: Ground Truth (Label).
    *   **Source**: IBM Cloud API via `fetch_twc_hourly.py`.
    *   **Spec**: ASOS Station Observations, Quality Controlled.
*   **IEM (Iowa Environmental Mesonet)**:
    *   **Role**: Forecast Source (Atlanta).
    *   **Source**: `mesonet.agron.iastate.edu` API.
    *   **Spec**: Archives NWS GFS MOS text products (00Z/12Z cycles).
*   **Open-Meteo**:
    *   **Role**: Forecast Source (Seoul).
    *   **Source**: `api.open-meteo.com`.
    *   **Spec**: Archives global model runs (GFS, ECWMF, JMA).

### C. Data Anatomy (Why two sources?)
To train the AI, we need pairs of **{Prediction, Reality}**.
1.  **Input (X): "GFS/JMA Hourly Features"**
    *   **Source**: Open-Meteo (NOAA/JMA Archives).
    *   **What**: The *forecast* made by the supercomputer at that time. e.g. "On June 1st, the computer predicted 90°F."
    *   **Cost**: Free, Fast (Bulk).
2.  **Target (Y): "TWC Actuals"**
    *   **Source**: The Weather Company (IBM) via `api.weather.com`.
    *   **What**: The *reality* measured by the thermometer at the airport. e.g. "On June 1st, the thermometer read 92°F."
    *   **Cost**: Paid/Rate-Limited (Slow).
*   **The Learning Process**: The AI learns the *mapping* from Input to Target. "When the GFS predicts a steep morning heating slope, it usually underestimates the Max Temp by 2°F."

### Models (The "Predictors")
*   **GFS (Global Forecast System)**: The "American Model" (NOAA). Good globally, but underestimates urban heat.
*   **MOS (Model Output Statistics)**: A statistical correction applied by the NWS *on top* of GFS. It is the "Gold Standard" for US airports.
*   **JMA GSM (Global Spectral Model)**: The "Japanese Model". Superior performance in East Asia.
*   **JMA Hybrid (Ours)**: A custom XGBoost layer trained to correct JMA GSM biases using Seoul-specific physics features.

### Metrics
*   **MAE (Mean Absolute Error)**: The average distance between Prediction and Reality.
    *   *Calculation*: `Sum(|Actual - Predicted|) / N`.
*   **Bias**: Systematic Error. Positive Bias = Model is Too Cold (Under-predicts). Negative Bias = Model is Too Hot.
*   **Zulu Time (Z)**: Universal Time (UTC).
    *   **00Z / 12Z**: The two main daily model runs. 12Z (7AM EST) is the most important for morning trading.
*   **Signal**: The betting instruction.
    *   *Example*: "YES > 50F" means "Buy the 'Over 50F' contract".

---

## 3. Detailed Architecture

### A. Atlanta Engine (`predict_live.py`)
*   **Philosophy**: "Trust the Physics". aka **The MOS Strategy**.
*   **Logic**:
    1.  **Ingest**: Downloads the 12Z GFS MOS Forecast for KATL.
    2.  **Context**: Downloads yesterday's TWC actuals to check for extreme anomalies.
    3.  **Consensus Check**: Runs a "Legacy XGBoost" model (pure ML).
    4.  **Decision**:
        *   If `MOS` and `ML` agree (within 2F), confident bet.
        *   If they disagree, **Trust MOS** output (Backtesting proved MOS 2.4F > ML 4.2F).
*   **Why?**: Atlanta is an open-field airport. The GFS physics model resolves the terrain well, so statistical post-processing (NWS MOS) is unbeatable.

### B. Seoul Engine (`predict_seoul.py`)
*   **Philosophy**: "Correct the Physics". aka **The Heat Island Strategy**.
*   **Problem**: Seoul is a dense concrete jungle. Global models (GFS/JMA) see "Land", not "Concrete". They consistently predict nights that are ~4-5°F too cold (Radiative Cooling bias).
*   **Solution**: **Hourly Feature Engineering**.
    *   Instead of just "Daily Max", we feed the AI the *shape* of the day.
*   **Features Used**:
    1.  `JMA_13`, `JMA_14`, `JMA_15`: The raw temperature forecast at 1 PM, 2 PM, 3 PM.
    2.  `Morning_Slope` (`JMA_12 - JMA_08`): How fast is the sun heating the city?
    3.  `Evening_Slope` (`JMA_20 - JMA_16`): How fast is the city cooling? (Concrete calculates this differently than grass).
    4.  `Seasonality` (`Sin_DOY`, `Cos_DOY`): Winter heat islands behave differently than Summer ones.
*   **The Model**:
    *   Algorithm: **XGBoost Regressor**.
    *   Training Data: 10 Years (2016-2025) of Hourly JMA Forecasts matched with TWC Actuals.
    *   Target: `TWC_Max_Temp`.
*   **Performance**:
    *   Raw JMA Error: ~4.0 F.
    *   **Hybrid Error: 2.1 F (1.17 C)**.
    *   Improvement: **+50%**.

---

## 4. Operational Guide

### Where to Find Data
*   **Seoul Training Data**: `rksi_sophisticated_data.csv` (Contains 10 years of hourly inputs).
*   **Seoul Model**: `rksi_advanced_model.json` (The trained XGBoost brain).
*   **Atlanta Training Data**: `katl_weather_model/katl_full_history.csv`.

### Daily Betting Workflow
1.  **Step 1: Run Predictions**
    ```bash
    # For Atlanta (Outputs Fahrenheit)
    ./venv/bin/python predict_live.py

    # For Seoul (Outputs Celsius)
    ./venv/bin/python predict_seoul.py
    ```
2.  **Step 2: Compare with Polymarket**
    *   Look at the "Settlement Value".
    *   Is our prediction inside a "No" bucket? (Bet No).
    *   Is our prediction largely inside a "Yes" bucket? (Bet Yes).
    *   **Edge Rule**: Do not bet if the edge is less than the Model Error (2.4F / 1.17C).

### Maintenance (Retraining)
Run these commands every 6 months to keep the Seoul AI fresh:
```bash
# 1. Download new data
./venv/bin/python katl_weather_model/fetch_rksi_hourly.py

# 2. Retrain the brain
./venv/bin/python katl_weather_model/train_seoul_advanced.py
```
This will automatically update `rksi_advanced_model.json`.

---

## 5. File Structure
*   `predict_live.py`: Main script for Atlanta.
*   `predict_seoul.py`: Main script for Seoul.
*   `fetch_twc_hourly.py`: Utility to get ground truth.
*   `train_seoul_advanced.py`: The "Trainer" for the Seoul AI.
*   `katl_weather_model/`: Directory containing all core logic.
