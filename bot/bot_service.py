import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bot.config import Config
import pytz

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Scheduler
scheduler = AsyncIOScheduler(timezone=Config.TIMEZONE)

# --- JoBS ---

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
    if 'latest_chat_id' in context.bot_data:
        cid = context.bot_data['latest_chat_id']
        await context.bot.send_message(chat_id=cid, text=result, parse_mode='Markdown')
    else:
        logger.warning("No Chat ID found to push notification. Run /start first.")

async def seoul_wrapper_job(context: ContextTypes.DEFAULT_TYPE):
    """Seoul Prediction Job"""
    logger.info("🇰🇷 Triggering Seoul Prediction...")
    from bot.jobs.seoul_job import run_seoul_cycle
    
    result = await asyncio.to_thread(run_seoul_cycle)
    logger.info(f"SEOUL REPORT:\n{result}")
    
    if 'latest_chat_id' in context.bot_data:
        cid = context.bot_data['latest_chat_id']
        await context.bot.send_message(chat_id=cid, text=result, parse_mode='Markdown')

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
    if 'latest_chat_id' in context.bot_data:
         cid = context.bot_data['latest_chat_id']
         await context.bot.send_message(chat_id=cid, text=f"⏱️ **Hourly Watcher (ATL)**\n{res_atl}\n\n🇰🇷 **Seoul**\n{res_sel}", parse_mode='Markdown')


# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    context.bot_data['latest_chat_id'] = cid
    await context.bot.send_message(chat_id=cid, text="🔮 The Oracle is Online. I will ping you here at 11am and 10pm.")


# --- Main ---

async def post_init(application: ApplicationBuilder):
    """
    Start the scheduler AFTER the bot's event loop is running.
    """
    logger.info("⚡️ Post-Init: Starting Scheduler...")
    scheduler.start()
    logger.info(f"✅ Scheduler started. ATL: {Config.RUN_TIME_EST}, SEL: 22:00, Watcher: Hourly")

def main():
    # Pass post_init to the builder
    application = ApplicationBuilder().token(Config.TELEGRAM_TOKEN).post_init(post_init).build()
    
    # 1. Handlers
    application.add_handler(CommandHandler('start', start))

    # 2. Scheduler Setup (Define jobs, but don't start yet)
    
    # A. Heartbeat (Hourly)
    scheduler.add_job(health_check_job, 'interval', minutes=60, args=[application])
    
    # B. Atlanta Daily (11:00 AM ET)
    h_atl, m_atl = map(int, Config.RUN_TIME_EST.split(":"))
    trigger_atl = CronTrigger(hour=h_atl, minute=m_atl, timezone=Config.TIMEZONE)
    scheduler.add_job(daily_prediction_job, trigger_atl, args=[application])
    
    # C. Seoul Daily (10:00 PM ET)
    trigger_korea = CronTrigger(hour=22, minute=0, timezone=Config.TIMEZONE)
    scheduler.add_job(seoul_wrapper_job, trigger_korea, args=[application])

    # D. Hourly Watcher (Interval)
    scheduler.add_job(hourly_watcher_job, 'interval', minutes=60, args=[application])
    
    # 3. Run Bot (This creates the loop and calls post_init)
    application.run_polling()

if __name__ == '__main__':
    main()
