import uvicorn
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from pydantic import BaseModel
from typing import Optional, Union
from datetime import datetime
from dotenv import load_dotenv
from .api import router, initialise_api
from .ge_automatic_email_tracking import process_supervisors

load_dotenv()
app = FastAPI()

# Environment variables
ALLOWED_ORIGINS = [
    os.getenv('FRONTEND_URL', 'http://localhost:3000'),
    'http://172.24.29.224:3000',  # Your specific frontend URL
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8000',
    'http://127.0.0.1:8000'
]

API_KEY = os.getenv('API_KEY')

if not API_KEY:
    raise ValueError("API_KEY must be set in environment variables")

# Initialise API with the API key
initialise_api(API_KEY)

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

# Schedule models
class ScheduleBase(BaseModel):
    job_id: Optional[str] = None

class ImmediateEmailSchedule(ScheduleBase):
    send_now: bool = True

class OneTimeEmailSchedule(ScheduleBase):
    schedule_time: datetime # "2024-11-25T09:00:00"

class RecurringEmailSchedule(ScheduleBase):
    cron_expression: str # "30 8 * * FRI" for every Friday at 8:30 AM
    description: Optional[str] = None

class EmailScheduleRequest(BaseModel):
    schedule_type: str  # "immediate", "one_time", or "recurring"
    schedule: Union[ImmediateEmailSchedule, OneTimeEmailSchedule, RecurringEmailSchedule]

class ScheduleResponse(BaseModel):
    success: bool
    message: str
    job_id: Optional[str] = None
    next_run_time: Optional[datetime] = None

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*", "X-API-Key", "Content-Type", "Authorisation"],
    expose_headers=["*"],
    max_age=86400,
)

scheduler = BackgroundScheduler()

def add_email_job(schedule_request: EmailScheduleRequest) -> ScheduleResponse:
    """Add a new email job to the scheduler based on schedule type."""
    try:
        schedule = schedule_request.schedule
        job_id = schedule.job_id or f"email_job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if schedule_request.schedule_type == "immediate":
            # Run job immediately
            process_supervisors()
            return ScheduleResponse(
                success=True,
                message="Email sent immediately",
                job_id=job_id,
                next_run_time=datetime.now()
            )

        elif schedule_request.schedule_type == "one_time":
            if not isinstance(schedule, OneTimeEmailSchedule):
                raise ValueError("Invalid schedule type for one-time email")
                
            # Schedule one-time job
            job = scheduler.add_job(
                process_supervisors,
                trigger=DateTrigger(run_date=schedule.schedule_time),
                id=job_id
            )
            return ScheduleResponse(
                success=True,
                message=f"Email scheduled for {schedule.schedule_time}",
                job_id=job.id,
                next_run_time=job.next_run_time
            )

        elif schedule_request.schedule_type == "recurring":
            if not isinstance(schedule, RecurringEmailSchedule):
                raise ValueError("Invalid schedule type for recurring email")
                
            # Schedule recurring job
            job = scheduler.add_job(
                process_supervisors,
                trigger=CronTrigger.from_crontab(schedule.cron_expression),
                id=job_id,
                name=schedule.description or f"Recurring email job {job_id}"
            )
            return ScheduleResponse(
                success=True,
                message=f"Recurring email scheduled with expression: {schedule.cron_expression}",
                job_id=job.id,
                next_run_time=job.next_run_time
            )
        else:
            raise ValueError(f"Invalid schedule type: {schedule_request.schedule_type}")

    except Exception as e:
        logger.error(f"Failed to schedule email job: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

app.include_router(router, prefix="/api")

# Direct app routes (non-API endpoints)
@app.get("/scheduled-jobs")
async def get_scheduled_jobs():
    """Get all scheduled email jobs."""
    jobs = scheduler.get_jobs()
    return {
        "jobs": [
            {
                "job_id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
    }

@app.get("/health")
async def health_check():
    """Application health check endpoint."""
    return {
        "status": "healthy",
        "scheduler": scheduler.running
    }

@app.post("/schedule-email")
async def schedule_email(request: EmailScheduleRequest) -> ScheduleResponse:
    """Schedule an email with specified timing."""
    return add_email_job(request)

@app.delete("/cancel-job/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a scheduled job."""
    try:
        scheduler.remove_job(job_id)
        return {"success": True, "message": f"Job {job_id} cancelled"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job not found: {str(e)}")

def start_scheduler():
    """Initialize and start the APScheduler."""
    try:
        scheduler.start()
        logger.info("APScheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        start_scheduler()
        
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