# backend/api.py
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from io import StringIO
# Import functions from your script
from .ge_automatic_email_tracking import (
    load_data,
    process_supervisors,
    generate_chart,
    create_email_content,
    send_email
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    try:
        # Read the uploaded file content
        contents = await file.read()
        # Convert bytes to string
        csv_string = contents.decode()
        # Convert string to StringIO object for pandas
        csv_stringio = StringIO(csv_string)
        
        # Load the CSV data
        data = pd.read_csv(csv_stringio, skiprows=1)
        
        # Process the data and send emails
        process_supervisors(data)
        
        return {
            "success": True,
            "message": "CSV processed and emails sent successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/preview-chart")
async def preview_chart(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        csv_string = contents.decode()
        csv_stringio = StringIO(csv_string)
        
        data = pd.read_csv(csv_stringio, skiprows=1)
        chart = generate_chart(data)
        
        return {
            "success": True,
            "chart": chart
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/test-email")
async def test_email(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        csv_string = contents.decode()
        csv_stringio = StringIO(csv_string)
        
        data = pd.read_csv(csv_stringio, skiprows=1)
        chart = generate_chart(data)
        
        # Send a test email to a specific address
        test_email = "223144086@ge.com"  # Use your test email
        email_content = create_email_content({
            'Total': 100,
            'Completion': 75,
            'Past Due': 15,
            'Pending': 10
        })
        
        send_email(test_email, "Test Email - CSV Upload Portal", email_content, chart)
        
        return {
            "success": True,
            "message": f"Test email sent to {test_email}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }