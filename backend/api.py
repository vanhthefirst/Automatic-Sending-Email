from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from io import StringIO
from typing import Dict, Any
from datetime import datetime
import logging
import traceback

# Import functions from your script
from .ge_automatic_email_tracking import (
    load_data,
    process_supervisors,
    generate_chart,
    create_email_content,
    send_email,
    get_course_unit_2_indices
)

# Configure logging
logging.basicConfig(
    filename='api.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint to verify the API is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        logging.info(f"Processing CSV upload: {file.filename}")
        
        # Read the uploaded file content
        contents = await file.read()
        csv_string = contents.decode()
        csv_stringio = StringIO(csv_string)
        
        # Load the CSV data
        data = pd.read_csv(csv_stringio, skiprows=1)
        
        # Process the data and send emails
        process_supervisors(data)
        
        logging.info("CSV processing completed successfully")
        return {
            "success": True,
            "message": "CSV processed and emails sent successfully",
            "filename": file.filename,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        error_msg = f"Error processing CSV: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )

@app.post("/api/preview-chart")
async def preview_chart(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        logging.info(f"Generating chart preview for: {file.filename}")
        
        contents = await file.read()
        csv_string = contents.decode()
        csv_stringio = StringIO(csv_string)
        
        data = pd.read_csv(csv_stringio, skiprows=1)
        chart = generate_chart(data)
        
        logging.info("Chart generation completed successfully")
        return {
            "success": True,
            "chart": chart,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        error_msg = f"Error generating chart: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )

@app.post("/api/test-email")
async def test_email(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        logging.info("Processing test email request")
        
        contents = await file.read()
        csv_string = contents.decode()
        csv_stringio = StringIO(csv_string)
        
        data = pd.read_csv(csv_stringio, skiprows=1)
        chart = generate_chart(data)
        
        # Send a test email to a specific address
        test_email = "223144086@ge.com"
        
        # Get the first supervisor's data for the test email
        start_idx, end_idx = get_course_unit_2_indices(data)
        first_supervisor_data = data.iloc[start_idx]
        
        email_content = create_email_content({
            'Total': pd.to_numeric(first_supervisor_data.iloc[10], errors='coerce'),
            'Completion': pd.to_numeric(first_supervisor_data.iloc[11], errors='coerce'),
            'Past Due': pd.to_numeric(first_supervisor_data.iloc[13], errors='coerce'),
            'Pending': pd.to_numeric(first_supervisor_data.iloc[14], errors='coerce')
        })
        
        send_email(test_email, "Test Email - CSV Upload Portal", email_content, chart)
        
        logging.info(f"Test email sent successfully to {test_email}")
        return {
            "success": True,
            "message": f"Test email sent to {test_email}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        error_msg = f"Error sending test email: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )

# Error handler for generic exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    error_msg = f"Unhandled error: {str(exc)}"
    logging.error(f"{error_msg}\n{traceback.format_exc()}")
    return {
        "success": False,
        "error": error_msg,
        "timestamp": datetime.now().isoformat()
    }