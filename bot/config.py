import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN_HERE")
    TWC_API_KEY = os.getenv("TWC_API_KEY", "YOUR_TWC_KEY")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "122628236") # Default to user provided ID for ease
    # Scheduler
    RUN_TIME_EST = "11:00"
    TIMEZONE = "America/New_York"
