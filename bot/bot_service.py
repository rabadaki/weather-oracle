import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from bot.config import Config
import pytz
import datetime

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- JOBS (Unchanged Logic, Adjusted Signature) ---

async def health_check_job(context: ContextTypes.DEFAULT_TYPE):
    """Simple heartbeat logging"""
    logger.info("💓 Heartbeat: The Oracle is observing.")

async def daily_prediction_job(context: ContextTypes.DEFAULT_TYPE):
    """The Main Event (Atlanta)"""
    logger.info("🚀 Triggering Daily Prediction Sequence (ATL)...")
    
    # Run Sync Job in Thread
    from bot.jobs.predict_job import run_prediction_cycle
    result = await asyncio.to_thread(run_prediction_cycle)
    
    logger.info(f"REPORT:\n{result}")
    
    # Send Notification
    # Send Notification
    chat_id = context.bot_data.get('latest_chat_id', Config.TELEGRAM_CHAT_ID)
    
    if chat_id:
        await context.bot.send_message(chat_id=chat_id, text=result, parse_mode='Markdown')
    else:
        logger.warning("No Chat ID found. Run /start or set TELEGRAM_CHAT_ID env var.")

async def seoul_wrapper_job(context: ContextTypes.DEFAULT_TYPE):
    """Seoul Prediction Job"""
    logger.info("🇰🇷 Triggering Seoul Prediction...")
    from bot.jobs.seoul_job import run_seoul_cycle
    
    result = await asyncio.to_thread(run_seoul_cycle)
    logger.info(f"SEOUL REPORT:\n{result}")
    
    logger.info(f"SEOUL REPORT:\n{result}")
    
    chat_id = context.bot_data.get('latest_chat_id', Config.TELEGRAM_CHAT_ID)
    if chat_id:
        await context.bot.send_message(chat_id=chat_id, text=result, parse_mode='Markdown')

async def hourly_watcher_job(context: ContextTypes.DEFAULT_TYPE):
    """Hourly Opportunity Watcher"""
    logger.info("👀 Watcher: Scanning for Intraday Opportunities...")
    
    from bot.jobs.predict_job import run_prediction_cycle
    from bot.jobs.seoul_job import run_seoul_cycle
    
    # 1. Atlanta
    res_atl = await asyncio.to_thread(run_prediction_cycle)
    logger.info(f"Hourly ATL: {res_atl}")
    
    # 2. Seoul
    res_sel = await asyncio.to_thread(run_seoul_cycle)
    logger.info(f"Hourly SEL: {res_sel}")
    
    # Notification (Verbose Mode)
    # Notification (Verbose Mode)
    chat_id = context.bot_data.get('latest_chat_id', Config.TELEGRAM_CHAT_ID)
    if chat_id:
         await context.bot.send_message(chat_id=chat_id, text=f"⏱️ **Hourly Watcher (ATL)**\n{res_atl}\n\n🇰🇷 **Seoul**\n{res_sel}", parse_mode='Markdown')


# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    context.bot_data['latest_chat_id'] = cid
    await context.bot.send_message(chat_id=cid, text="🔮 The Oracle is Online. I will ping you here at 11am and 10pm.")


# --- Main ---

def main():
    # Build Application
    application = ApplicationBuilder().token(Config.TELEGRAM_TOKEN).build()
    
    # 1. Handlers
    application.add_handler(CommandHandler('start', start))

    # 2. Job Queue Setup (Native PTB)
    job_queue = application.job_queue
    
    # A. Heartbeat (Hourly)
    job_queue.run_repeating(health_check_job, interval=3600, first=10)
    
    # B. Atlanta Daily (11:00 AM ET)
    # Parse Time
    h_atl, m_atl = map(int, Config.RUN_TIME_EST.split(":"))
    # PTB JobQueue uses datetime.time with timezone
    t_atl = datetime.time(hour=h_atl, minute=m_atl, tzinfo=pytz.timezone(Config.TIMEZONE))
    job_queue.run_daily(daily_prediction_job, time=t_atl)
    
    # C. Seoul Daily (10:00 PM ET)
    t_sel = datetime.time(hour=22, minute=0, tzinfo=pytz.timezone(Config.TIMEZONE))
    job_queue.run_daily(seoul_wrapper_job, time=t_sel)

    # D. Hourly Watcher (Interval)
    job_queue.run_repeating(hourly_watcher_job, interval=3600, first=60)
    
    logger.info(f"JobQueue started. ATL: {t_atl}, SEL: {t_sel}, Watcher: Hourly")
    
    # 3. Run Bot
    application.run_polling()

if __name__ == '__main__':
    main()
