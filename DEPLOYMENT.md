# Deployment Guide: "The Oracle"

## 1. GitHub Setup
I have initialized the local repository. You just need to push it.

1.  **Create a New Repo** on your GitHub (e.g., `weather-oracle`).
2.  **Push the Code**:
    ```bash
    cd weather-model
    git remote add origin https://github.com/YOUR_USERNAME/weather-oracle.git
    git branch -M main
    git push -u origin main
    ```

## 2. Railway Setup
Deploying to Railway is the easiest way to keep the bot running 24/7.

1.  **Login to [Railway.app](https://railway.app)**.
2.  **New Project** -> **Deploy from GitHub repo**.
3.  Select `weather-oracle`.
4.  **Wait for Build**: Railway will detect the `Dockerfile` and build it automatically.

## 3. Configuration (Critical)
You must set the Environment Variables in Railway settings:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `TELEGRAM_TOKEN` | `...` | Your Bot Token from BotFather |
| `TWC_API_KEY` | `...` | Your Weather Company API Key |
| `TELEGRAM_CHAT_ID` | `122628236` | Your User ID (for persistent alerts) |
| `TIMEZONE` | `US/Eastern` | Bot Timezone (Default) |
| `RUN_TIME_EST` | `11:00` | Daily Run Time |

## 4. Verification
Once deployed:
1.  Check the **Deploy Logs** in Railway. You should see:
    > `Scheduler started. ATL: 11:00, SEL: 22:00, Watcher: Hourly`
2.  Go to Telegram and typ `/predict` (or wait for the hourly watcher).

## 5. Troubleshooting
*   **Asset Missing**: If the bot crashes saying `rksi_advanced_model.json not found`, ensure you **committed** the JSON model files. (My `.gitignore` excludes CSVs but includes JSONs, so it should be fine).
