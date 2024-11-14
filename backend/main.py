import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel
from typing import Optional
import logging
from api import app
from .ge_automatic_email_tracking import run_scheduled_job
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API Key security setup
API_KEY_NAME = "X-API-Key"
API_KEY = "your-secret-api-key-here"  # Store this securely in environment variables
api_key_header = APIKeyHeader(name=API_KEY_NAME)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-API-Key"],  # Include API Key header
    expose_headers=["*"]
)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=401,
        detail="Invalid API Key"
    )

# Request models
class EmailRequest(BaseModel):
    recipient: str
    subject: Optional[str] = None
    body: Optional[str] = None

class ScheduleEmailRequest(EmailRequest):
    schedule_time: datetime
    day_of_week: Optional[str] = None  # 'mon', 'tue', etc.
    hour: Optional[int] = None
    minute: Optional[int] = None
    is_recurring: bool = False

# Initialize the scheduler
scheduler = BackgroundScheduler()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scheduler_running": scheduler.running
    }

@app.post("/send-email")
async def send_email(
    email_request: EmailRequest,
    api_key: str = Depends(get_api_key)
):
    try:
        logger.info(f"Attempting to send email to {email_request.recipient}")
        result = run_scheduled_job(
            recipient=email_request.recipient,
            subject=email_request.subject,
            body=email_request.body
        )
        logger.info("Email sent successfully")
        return {"status": "success", "message": "Email sent successfully"}
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/schedule-email")
async def schedule_email(
    schedule_request: ScheduleEmailRequest,
    api_key: str = Depends(get_api_key)
):
    try:
        if schedule_request.is_recurring:
            if not all([schedule_request.day_of_week, schedule_request.hour, schedule_request.minute]):
                logger.error("Missing required fields for recurring email")
                raise HTTPException(
                    status_code=400,
                    detail="For recurring emails, day_of_week, hour, and minute are required"
                )
            
            logger.info(f"Scheduling recurring email for {schedule_request.recipient}")
            # Schedule recurring job
            job = scheduler.add_job(
                run_scheduled_job,
                'cron',
                day_of_week=schedule_request.day_of_week,
                hour=schedule_request.hour,
                minute=schedule_request.minute,
                args=[
                    schedule_request.recipient,
                    schedule_request.subject,
                    schedule_request.body
                ]
            )
            return {
                "status": "success",
                "message": "Email scheduled recurring",
                "job_id": job.id
            }
        else:
            logger.info(f"Scheduling one-time email for {schedule_request.recipient}")
            # Schedule one-time job
            job = scheduler.add_job(
                run_scheduled_job,
                'date',
                run_date=schedule_request.schedule_time,
                args=[
                    schedule_request.recipient,
                    schedule_request.subject,
                    schedule_request.body
                ]
            )
            return {
                "status": "success",
                "message": "Email scheduled one-time",
                "job_id": job.id
            }
    except Exception as e:
        logger.error(f"Failed to schedule email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/cancel-scheduled-email/{job_id}")
async def cancel_scheduled_email(
    job_id: str,
    api_key: str = Depends(get_api_key)
):
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Cancelled scheduled email with job ID: {job_id}")
        return {"status": "success", "message": "Scheduled email cancelled"}
    except Exception as e:
        logger.error(f"Failed to cancel scheduled email: {str(e)}")
        raise HTTPException(status_code=404, detail="Scheduled email not found")

@app.get("/scheduled-emails")
async def get_scheduled_emails(
    api_key: str = Depends(get_api_key)
):
    try:
        jobs = scheduler.get_jobs()
        return {
            "scheduled_emails": [
                {
                    "job_id": job.id,
                    "next_run_time": job.next_run_time,
                    "trigger": str(job.trigger)
                }
                for job in jobs
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get scheduled emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def start_scheduler():
    try:
        scheduler.start()
        logger.info("APScheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        # Start the scheduler
        start_scheduler()
        
        # Add default Wednesday 2:30 PM job if needed
        scheduler.add_job(
            run_scheduled_job,
            'cron',
            day_of_week='wed',
            hour=14,
            minute=30,
            id='default_wednesday_job'
        )
        
        # Run the FastAPI application
        logger.info("Starting FastAPI application...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Application failed to start: {str(e)}")
        raise