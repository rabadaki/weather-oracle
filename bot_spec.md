# Weather Prediction Bot: "The Oracle" - Technical Spec

## 1. Product Vision
A "Set and Forget" autonomous agent that monitors weather models, predicts Polymarket outcomes, and pushes high-conviction signals to Telegram. It generates Value by automating the friction of running manual scripts and checking spreadsheets.

## 2. Core Features (The "10x" Polish)

### A. Autonomous Schedule (The Loop)
*   **07:00 AM ET**: "The Wake Up". Fetches initial guidance.
*   **11:00 AM ET**: "The World Report".
    *   **Atlanta**: Runs `predict_live.py` (GFS-MOS Priority).
    *   **Seoul**: Runs `predict_seoul.py` (JMA-Advanced).
    *   **Verdict**: Sends a consolidated report. "KATL: No on 50F | RKSI: Yes on 5C".

### B. "Smart" Notifications
Instead of spamming "Temp is 50F", the bot uses **logic**:
*   **Signal Strength**: "⚠️ **HIGH CONVICTION**" if Model vs Market Edge > 2°F.
*   **Context**: "Yesterday we predicted 49F, Actual was 50F. Accuracy: ✅ Good."
*   **Market Context**: "Model says **No** on 'Max > 50F' (Edge: 3.5°F)."

### C. Self-Healing Data Pipeline
*   **Auto-Append**: Every day, the bot fetches *Yesterday's* Actuals and appends them to `katl_full_history.csv`.
*   **Retraining**: Once a month (or when N=30 new samples), it spawns a background process to re-optimize the XGBoost weights. "The model gets smarter every month."

### D. Interactive Commands
*   `/predict`: Force run right now.
*   `/status`: Show data freshness ("Last GFS: 2 hours ago").
*   `/history`: Show last 5 days performance (Win Rate).

---

## 3. Architecture Stack

*   **Language**: Python 3.12
*   **Core Lib**: `python-telegram-bot` (Async, robust).
*   **Scheduling**: `APScheduler` (Better than `while True: sleep`). Handles missed jobs and timezones.
*   **State Management**: `sqlite3` (Simple `bot_state.db`). Stores:
    *   Last Prediction Sent.
    *   User Preferences (if multi-user).
    *   Performance Log.

## 4. Implementation Steps

### Phase 1: The Core (Push)
1.  **`bot_service.py`**: A daemon that initializes the Scheduler.
2.  **`jobs/predict_job.py`**: Wraps our existing `predict_live.py`. Captures STDOUT, parses the "Final Prediction" number.
3.  **`notifiers/telegram.py`**: Formats the message with Emojis and sends it.

### Phase 2: The Data Loop (Maintain)
1.  **`jobs/update_data.py`**: Runs `fetch_twc_hourly.py` for "Yesterday".
2.  **`utils/csv_manager.py`**: Appends the new row to the Master CSV.

### Phase 3: The Polish (Interactive)
1.  Add Command Handlers (`/start`, `/check`).
2.  Add Error Reporting (Ping Admin if API fails).

### Phase 4: Market Intelligence (The "Scanner")
1.  **`jobs/market_scanner.py`**:
    *   **Source 1: Discovery** (Gamma API):
        *   Query `https://gamma-api.polymarket.com/events?tag_id=Weather`.
        *   Find Event -> Get `market_slug` -> Get `token_id` for "Yes" and "No".
    *   **Source 2: Pricing** (CLOB API):
        *   Query `https://clob.polymarket.com/price?token_id=...&side=SELL`.
        *   Get the *executable price*.
    *   **Output**: Returns the *Strike Price* (50) and *Real-Time Price* (e.g. 0.45).
    *   **Integration**: The Prediction Job compares `Model(54)` vs `Strike(50)` to generate the Signal.

## 5. Security & Config
*   **Secrets**: `.env` file for `TELEGRAM_TOKEN`, `TWC_API_KEY`.
*   **Deployment**: `Dockerfile` provided for 24/7 server running (Railway/Render compatible).
