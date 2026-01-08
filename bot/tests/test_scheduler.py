import asyncio
import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

# Mock Job
flag = False
async def mock_job():
    global flag
    flag = True
    print("Job Executed!")

@pytest.mark.asyncio
async def test_scheduler_triggers():
    global flag
    flag = False
    
    scheduler = AsyncIOScheduler()
    run_date = datetime.now() + timedelta(seconds=1)
    
    scheduler.add_job(mock_job, 'date', run_date=run_date)
    scheduler.start()
    
    print(f"Waiting for job scheduled at {run_date}...")
    await asyncio.sleep(2)
    
    assert flag is True, "Scheduler failed to trigger job"
    scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(test_scheduler_triggers())
