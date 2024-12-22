from fastapi import FastAPI, APIRouter, HTTPException, Response, UploadFile, File, Security, Depends, Form
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
from io import BytesIO
import pandas as pd
import base64
import logging
import json
from datetime import datetime
from .ge_automatic_email_tracking import (
    process_supervisors,
    generate_chart,
    get_course_unit_2_indices,
    safe_convert_to_float,
    create_email_content,
    send_test_email  # Add this to ge_automatic_email_tracking.py
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='api_endpoints.log'
)
logger = logging.getLogger(__name__)

app = FastAPI()
router = APIRouter()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/test")
async def test_route():
    return {"message": "Test route is working"}

@app.on_event("startup")
async def list_routes():
    for route in app.routes:
        print(route.path, route.methods)

class EmailTemplate(BaseModel):
    subject: str
    greeting: str
    intro: str
    action: str
    closing: str
    sendTestCopy: Optional[bool] = False

class PreviewResponse(BaseModel):
    success: bool
    chart: str  # Base64 encoded chart image
    content: str  # HTML email content
    metrics: Dict[str, float]
    sendTestEmail: Optional[bool] = False

class ProcessResponse(BaseModel):
    success: bool
    message: str
    filename: str
    timestamp: str
    processed_rows: int
    email_success: Optional[int]
    email_failure: Optional[int]

class ErrorDetail(BaseModel):
    detail: str

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=401,
        detail="Invalid API Key"
    )

def initialise_api(api_key: str):
    global API_KEY
    API_KEY = api_key

@router.options("/upload-csv", include_in_schema=False)
@router.options("/preview-email", include_in_schema=False)
@router.options("/process-emails", include_in_schema=False)
@router.options("/send-test-email", include_in_schema=False)
async def options_handler(response: Response):
    response.headers.update({
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-API-Key",
        "Access-Control-Max-Age": "86400",
    })
    return {}

def validate_csv(df: pd.DataFrame) -> bool:
    try:        
        if len(df) < 1:
            raise ValueError("CSV file is empty")
            
        # Check if we can find the Course Units section
        start_idx, end_idx = get_course_unit_2_indices(df)
        if start_idx is None or end_idx is None:
            raise ValueError("Could not find Course Units section in CSV")
            
        return True
        
    except Exception as e:
        logger.error(f"CSV validation failed: {str(e)}")
        raise ValueError(f"CSV validation failed: {str(e)}")

def get_row_metrics(data: pd.DataFrame, row_index: int) -> Dict[str, float]:
    try:
        row = data.iloc[row_index]
        metrics = {
            'total': safe_convert_to_float(row.iloc[10]),
            'completed': safe_convert_to_float(row.iloc[11]),
            'past_due': safe_convert_to_float(row.iloc[13]),
            'pending': safe_convert_to_float(row.iloc[14])
        }
        
        # Calculate completion rate
        metrics['completion_rate'] = (
            (metrics['completed'] / metrics['total'] * 100) 
            if metrics['total'] > 0 else 0
        )
        
        return metrics
    except Exception as e:
        logger.error(f"Error extracting metrics from row {row_index}: {str(e)}")
        raise ValueError(f"Error extracting metrics: {str(e)}")

@router.post("/upload-csv")
async def upload_csv(
    response: Response,
    file: UploadFile = File(...),
    # api_key: str = Depends(get_api_key)
) -> ProcessResponse:
    try:
        # Read CSV content
        content = await file.read()
        df = pd.read_csv(BytesIO(content))
        
        # Validate CSV structure
        if not validate_csv(df):
            raise ValueError("Invalid CSV structure")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return ProcessResponse(
            success=True,
            message="CSV file uploaded successfully",
            filename=file.filename,
            timestamp=timestamp,
            processed_rows=len(df)-2,
            email_success=None,
            email_failure=None
        )
        
    except Exception as e:
        logger.error(f"Error uploading CSV: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/preview-email")
async def preview_email(
    response: Response,
    file: UploadFile = File(...),
    row_index: str = Form('0'),
) -> PreviewResponse:
    try:
        row_index = int(row_index)
        content = await file.read()
        df = pd.read_csv(BytesIO(content))
        
        if not validate_csv(df):
            raise ValueError("Invalid CSV structure")
        
        metrics = get_row_metrics(df, row_index)
        chart_bytes = generate_chart(df)
        chart_base64 = base64.b64encode(chart_bytes).decode()
        
        # Generate email content with template
        # template_dict = template.model_dump() if template else None
        email_content = create_email_content(metrics, None)
        
        return PreviewResponse(
            success=True,
            chart=chart_base64,
            content=email_content,
            metrics=metrics,
            sendTestEmail=False # Default value
        )
        
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/process-emails")
async def process_emails(
    response: Response,
    file: UploadFile = File(...),
    template: str = Form(None),
) -> ProcessResponse:
    try:
        # Read CSV content
        content = await file.read()
        df = pd.read_csv(BytesIO(content))

        template_data = json.loads(template) if template else {}
        print("Received template data:", template_data)
        send_test_copy = template_data.get('sendTestCopy', False)
        logger.info(f"Received sendTestCopy flag: {send_test_copy}")

        template_dict = {
            "subject": template_data.get('subject', "Training Tasks Update"),
            "greeting": template_data.get('greeting', "Dear Team Leader,"),
            "intro": template_data.get('intro', "This is a reminder about pending training tasks in your team:"),
            "action": template_data.get('action', "Please ensure your team completes any pending or past due tasks by this Friday.\nBelow is the chart to show the current status of your team and others:"),
            "closing": template_data.get('closing', "Best regards,\nHR Team")
        }

        # Validate CSV
        if not validate_csv(df):
            raise ValueError("Invalid CSV structure")
        
        # Process emails
        success_count, failure_count = process_supervisors(
            df, 
            template_dict, 
            send_test=send_test_copy
        )

        # Only attempt test email if specifically requested
        if send_test_copy:
            try:
                test_metrics = {
                    'total': 0,
                    'completed': 0,
                    'past_due': 0,
                    'pending': 0,
                    'completion_rate': 0
                }
                
                chart_bytes = generate_chart(df)
                test_success = send_test_email(template_dict, test_metrics, chart_bytes)
                if test_success:
                    success_count += 1
                else:
                    failure_count += 1
                logger.info(f"Test email sent successfully: {test_success}")
            except Exception as e:
                logger.error(f"Error sending test email: {str(e)}")
                failure_count += 1
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return ProcessResponse(
            success=True,
            message=f"Processed {success_count + failure_count} emails",
            filename=file.filename,
            timestamp=timestamp,
            processed_rows=len(df)-2,
            email_success=success_count,
            email_failure=failure_count
        )
        
    except Exception as e:
        logger.error(f"Error processing emails: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/health")
async def health_check(response: Response, api_key: str = Depends(get_api_key)):
    """Health check endpoint."""
    return {"status": "healthy"}

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)},
        headers={"Access-Control-Allow-Origin": "*"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={"Access-Control-Allow-Origin": "*"}
    )
    
app.include_router(router, prefix="/api")