import uvicorn
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from api import app
from datetime import datetime
from ge_automatic_email_tracking import run_scheduled_job

# Initialise the scheduler
scheduler = BackgroundScheduler()

# Add the job to run every Monday at 2:45 PM
scheduler.add_job(run_scheduled_job, 'cron', day_of_week='mon', hour=14, minute=45)

# Start the scheduler
scheduler.start()

if __name__ == "__main__":
    # Run the FastAPI application with uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)