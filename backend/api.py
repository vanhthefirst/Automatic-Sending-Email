from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from io import StringIO
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import traceback

# Import functions from your script
from .ge_automatic_email_tracking import (
    process_supervisors,
    generate_chart,
    create_email_content,
    send_email,
    get_course_unit_2_indices,
    safe_convert_to_float
)

# Enhanced logging configuration
logging.basicConfig(
    filename='api.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

app = FastAPI(title="CSV Processing API", version="1.0.0")

# Configure CORS with more specific settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

def validate_csv_data(data: pd.DataFrame) -> Optional[str]:
    """
    Validate the CSV data structure and content.
    Returns error message if validation fails, None if successful.
    """
    try:
        # Check if dataframe is empty
        if data.empty:
            return "CSV file is empty"
            
        # Check for required columns
        required_columns = [0, 10, 11, 13, 14]  # Column indices we need
        if not all(i < data.shape[1] for i in required_columns):
            return "CSV file is missing required columns"
            
        # Validate Course Units (2) section exists
        try:
            start_idx, end_idx = get_course_unit_2_indices(data)
            if start_idx is None or end_idx is None or start_idx >= end_idx:
                return "Invalid Course Units (2) section structure in the CSV"
        except ValueError as ve:
            return str(ve)
        except Exception as e:
            return f"Error validating Course Units (2) section: {str(e)}"
            
        return None
    except Exception as e:
        logger.error(f"Data validation error: {str(e)}")
        return f"Data validation failed: {str(e)}"

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Enhanced health check endpoint with more system information"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": "production"
    }

@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)) -> JSONResponse:
    try:
        logger.info(f"Processing CSV upload: {file.filename}")
        
        # Validate file extension
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Only CSV files are accepted"
            )
        
        # Read file content
        contents = await file.read()
        
        # Try different encodings
        for encoding in ['utf-8-sig', 'utf-8', 'utf-16']:
            try:
                csv_string = contents.decode(encoding)
                csv_stringio = StringIO(csv_string)
                data = pd.read_csv(csv_stringio)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise HTTPException(
                status_code=400,
                detail="Unable to decode CSV file. Please check the file encoding."
            )
        
        # Validate data structure
        validation_error = validate_csv_data(data)
        if validation_error:
            raise HTTPException(
                status_code=400,
                detail=validation_error
            )
        
        # Process the data and send emails
        success_count, failure_count = process_supervisors(data)
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"CSV processed: {success_count} emails sent successfully, {failure_count} failed",
                "filename": file.filename,
                "timestamp": datetime.now().isoformat(),
                "processed_rows": len(data),
                "email_success": success_count,
                "email_failure": failure_count
            },
            status_code=200
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        error_msg = f"Error processing CSV: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        error_msg = f"Error processing CSV: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )

@app.post("/api/preview-chart")
async def preview_chart(file: UploadFile = File(...)) -> JSONResponse:
    """
    Generate chart preview from uploaded CSV.
    Enhanced with proper error handling and response formatting.
    """
    try:
        logger.info(f"Generating chart preview for: {file.filename}")
        
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Only CSV files are accepted"
            )
        
        contents = await file.read()
        csv_string = contents.decode()
        csv_stringio = StringIO(csv_string)
        
        data = pd.read_csv(csv_stringio, skiprows=1)
        
        # Validate data before generating chart
        validation_error = validate_csv_data(data)
        if validation_error:
            raise HTTPException(
                status_code=400,
                detail=validation_error
            )
        
        chart = generate_chart(data)
        
        logger.info("Chart generation completed successfully")
        return JSONResponse(
            content={
                "success": True,
                "chart": chart.decode('utf-8') if isinstance(chart, bytes) else chart,
                "timestamp": datetime.now().isoformat()
            },
            status_code=200
        )
        
    except Exception as e:
        error_msg = f"Error generating chart: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Enhanced generic exception handler with more detailed error reporting"""
    error_msg = f"Unhandled error: {str(exc)}"
    logger.error(f"{error_msg}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url),
            "method": request.method
        }
    )