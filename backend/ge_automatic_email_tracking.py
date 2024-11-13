from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from io import BytesIO
from typing import Optional, Tuple
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
import schedule
import time
import os
import socket
import logging


def get_course_unit_2_indices(data):
    """Find the start and end indices for Course Units (2) section"""
    course_unit_2_start = None
    course_unit_2_end = None
    
    # First find the column that contains 'Course Units (2)'
    target_column = None
    for col in data.columns:
        if any(text in str(col) for text in "Course Unit (2)"):
            target_column = col
            course_unit_2_start = 0  # Start from the first data row
            break
    
    if target_column:
        # Now find where this section ends
        for idx in range(1, len(data)):
            if pd.isna(data.iloc[idx].iloc[0]) or str(data.iloc[idx].iloc[0]).strip() == '':
                course_unit_2_end = idx
                break
    
    # If we found the start but not the end (might be at the end of file)
    if course_unit_2_end is None and course_unit_2_start is not None:
        course_unit_2_end = len(data)
    
    # Add better error handling
    if course_unit_2_start is None:
        raise ValueError("Could not find Course Units (2) section in the CSV")
    if course_unit_2_end is None:
        raise ValueError("Could not determine the end of Course Units (2) section")
        
    return course_unit_2_start, course_unit_2_end


def generate_chart(data):
    data = data.iloc[:-3]  # Remove the last three rows which contain notes and totals
    start_idx, end_idx = get_course_unit_2_indices(data)
    data = data.iloc[start_idx:end_idx] # Extract only Course Units (2) data

    # Extract supervisor names and Course Units data
    supervisors = data.iloc[:, 0]

    # For Course Units, we want these specific columns:
    # Total is column index 10
    # Completion is column index 11
    # Past Due is column index 13
    # Pending is column index 14
    course_units_data = pd.DataFrame({
        'Supervisor': supervisors,
        'Total': pd.to_numeric(data.iloc[:, 10], errors='coerce'),
        'Completion': pd.to_numeric(data.iloc[:, 11], errors='coerce'),
        'Completion Rate': pd.to_numeric(data.iloc[:, 12], errors='coerce'),
        'Past Due': pd.to_numeric(data.iloc[:, 13], errors='coerce'),
        'Pending': pd.to_numeric(data.iloc[:, 14], errors='coerce')
    })

    # Clean up the data
    course_units_data = course_units_data.fillna(0)
    data_sorted = course_units_data.sort_values('Supervisor', ascending=False)

    # Create horizontal stacked bar chart
    fig, ax = plt.subplots(figsize=(15, len(data_sorted) * 0.5))

    # Create stacked bars
    ax.barh(data_sorted['Supervisor'], data_sorted['Completion'], 
            label='Completed', color='#1f77b4')
    ax.barh(data_sorted['Supervisor'], data_sorted['Pending'], 
            left=data_sorted['Completion'], label='Pending', color='#ff7f0e')
    ax.barh(data_sorted['Supervisor'], data_sorted['Past Due'], 
            left=data_sorted['Completion'] + data_sorted['Pending'], 
            label='Past Due', color='#d62728')

    # Customize the chart
    ax.set_xlabel('Number of Tasks')
    ax.set_title('Supervisors - Completed, Pending, and Past Due Tasks of Course Units')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3)

    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Add grid lines
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)

    # Calculate maximum total for x-axis limit
    max_total = data_sorted['Total'].max()

    # Add data labels
    for i, supervisor in enumerate(data_sorted['Supervisor']):
        completion = int(data_sorted['Completion'].iloc[i])
        pending = int(data_sorted['Pending'].iloc[i])
        past_due = int(data_sorted['Past Due'].iloc[i])
        
        # Create label string
        label = f"{completion} | {pending} | {past_due}"
        
        # Add label to the right of the bar
        ax.text(max_total * 1.02, i, label, va='center', ha='left', fontsize=9)

    # Extend x-axis to accommodate labels
    plt.xlim(0, max_total * 1.2)

    # Add vertical line to separate chart from labels
    ax.axvline(x=max_total, color='gray', linestyle='--', linewidth=0.8)

    plt.tight_layout()
    #plt.subplots_adjust(top=1)
   
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='jpg')
    img_buffer.seek(0)
    return img_buffer.getvalue()


def create_email_content(data_sorted):
    #name = data['Supervisor (SSO ID)'].split('[')[0].strip()
    total_tasks = data_sorted.get('Total', 'N/A')
    completed_tasks = data_sorted.get('Completion', 'N/A')
    completion_rate = str((completed_tasks / total_tasks * 100).round(2)).split('%')[0]
    pending_tasks = data_sorted.get('Pending', 'N/A')
    past_due_tasks = data_sorted.get('Past Due', 0) if pd.notna(data_sorted.get('Past Due')) else 0

    email_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ width: 100%; max-width: 100%px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f4f4f4; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .stats {{ margin-bottom: 20px; }}
            .chart-container {{ width: 100%; margin: 20px 0; text-align: center; background-color: white; padding: 10px; box-sizing: border-box; }}
            .chart-image {{ width: 100%; max-width: 100%; height: auto; display: block; margin: 0 auto; }}
            .footer {{ background-color: #f4f4f4; padding: 10px; text-align: center; font-size: 0.8em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Task Completion Reminder</h1>
            </div>
            <div class="content">
                <p>Dear People Leaders,</p>
                <p>Please remind your team members who have not been completed the Training to complete it by this Friday.</p>
                <p>Here are the progress of your team. Please take a moment to review pending and past due tasks. Your timely completion of these tasks is crucial:</p>
                <div class="stats">
                    <p><strong>Total Tasks:</strong> {total_tasks}</p>
                    <p><strong>Completed Tasks:</strong> {completed_tasks}</p>
                    <p><strong>Completion Rate:</strong> {completion_rate}%</p>
                    <p><strong>Pending Tasks:</strong> {pending_tasks}</p>
                    <p><strong>Past Due Tasks:</strong> {past_due_tasks}</p>
                </div>
                <div class="chart">
                    <p style="margin-bottom: 15px;">Here's a visual representation of task status under supervisors:</p>
                    <img src="cid:task_chart" 
                        alt="Task Status Chart" 
                        class="chart-image"
                        style="width: 100%; max-width: 100%px; height: auto; display: block; margin: 0 auto;
                                border: 1px solid #e0e0e0; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                </div>
                <p>If you have any questions or need assistance, please don't hesitate to reach out to your team lead or the HR department.</p>
                <p>Best regards,<br>HR Team</p>
            </div>
            <div class="footer">
                <p>This is an automated message. Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return email_content


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='email_tracking.log'
)
logger = logging.getLogger(__name__)


def extract_ssoID(supervisor_string: str) -> Optional[str]:
    """
    Extract SSO ID from supervisor string and return email address.
    Returns None if extraction fails.
    """
    try:
        if '[' in supervisor_string and ']' in supervisor_string:
            sso_id = supervisor_string.split('[')[-1].strip(']')
            email = f"{sso_id}@ge.com"
            logger.info(f"Successfully extracted email: {email}")
            return email
        else:
            logger.warning(f"No SSO ID found in string: {supervisor_string}")
            return None
    except Exception as e:
        logger.error(f"Error extracting SSO ID from {supervisor_string}: {str(e)}")
        return None


def send_email(recipient: str, subject: str, body: str, chart: bytes) -> bool:
    """
    Send email with enhanced error handling and logging.
    Returns True if email was sent successfully, False otherwise.
    """
    msg = MIMEMultipart()
    sender = os.getenv('SMTP_SENDER', '223144086@ge.com')
    msg['From'] = sender  # #extract_ssoID(supervisor)
    msg['To'] = recipient
    msg['Subject'] = "Course Unit Training Completion Status"
    
    # Attach email content
    msg.attach(MIMEText(body, 'html'))

    # Attach chart
    try:
        img = MIMEImage(chart)
        img.add_header('Content-ID', '<task_chart>')
        msg.attach(img)
    except Exception as e:
        logger.error(f"Error attaching chart: {str(e)}")
        return False

    # SMTP Configuration
    smtp_config = {
        'server': os.getenv('SMTP_SERVER', 'e2ksmtp01.e2k.ad.ge.com'),
        'port': int(os.getenv('SMTP_PORT', '25')),
        'username': os.getenv('SMTP_USERNAME', None),
        'password': os.getenv('SMTP_PASSWORD', None),
        'use_tls': os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'
    }

    try:
        logger.info(f"Attempting to connect to SMTP server {smtp_config['server']}:{smtp_config['port']}")
        with smtplib.SMTP(smtp_config['server'], smtp_config['port'], timeout=30) as server:
            server.set_debuglevel(1)  # Enable debug output
            server.ehlo()
            
            if smtp_config['use_tls']:
                try:
                    server.starttls()
                    server.ehlo()
                    logger.info("TLS connection established")
                except Exception as e:
                    logger.warning(f"TLS connection failed: {str(e)}")
            
            # Authenticate if credentials provided
            if smtp_config['username'] and smtp_config['password']:
                try:
                    server.login(smtp_config['username'], smtp_config['password'])
                    logger.info("SMTP authentication successful")
                except Exception as e:
                    logger.error(f"SMTP authentication failed: {str(e)}")
                    return False
            
            server.send_message(msg)
            logger.info(f"Email sent successfully to {recipient}")
            return True

    except socket.gaierror as e:
        logger.error(f"DNS lookup failed for {smtp_config['server']}: {str(e)}")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error sending email to {recipient}: {str(e)}")
    
    return False


def process_supervisors(data: pd.DataFrame) -> Tuple[int, int]:
    """
    Process supervisors and send emails. Returns tuple of (success_count, failure_count)
    """
    success_count = 0
    failure_count = 0
    
    try:
        start_idx, end_idx = get_course_unit_2_indices(data)
        if start_idx is None or end_idx is None:
            logger.error("Could not find Course Units (2) section in CSV")
            return success_count, failure_count
            
        course_unit_2_data = data.iloc[start_idx:end_idx]
        
        for index, row in course_unit_2_data.iterrows():
            try:
                supervisor = str(row.iloc[0]).strip()
                if pd.isna(supervisor) or supervisor == '':
                    continue
                    
                # Convert values with better error handling
                pending = pd.to_numeric(row.iloc[14], errors='coerce') or 0
                past_due = pd.to_numeric(row.iloc[13], errors='coerce') or 0
                total = pd.to_numeric(row.iloc[10], errors='coerce') or 0
                completion = pd.to_numeric(row.iloc[11], errors='coerce') or 0

                # Log the values for debugging
                logger.info(f"Processing supervisor {supervisor}: pending={pending}, past_due={past_due}")
                
                # Check if email should be sent (pending or past due tasks exist)
                if pending > 0 or past_due > 0:
                    recipient_email = extract_ssoID(supervisor)
                    
                    if recipient_email:
                        try:
                            # Generate chart for all data
                            chart = generate_chart(data)
                            
                            # Prepare row data for email
                            row_data = pd.Series({
                                'Total': total,
                                'Completion': completion,
                                'Past Due': past_due,
                                'Pending': pending
                            })
                            
                            # Create and send email
                            email_content = create_email_content(row_data)
                            if send_email(
                                recipient_email,
                                "Course Unit Training Completion Status",
                                email_content,
                                chart
                            ):
                                success_count += 1
                                logger.info(f"Email sent successfully to {recipient_email}")
                            else:
                                failure_count += 1
                                logger.error(f"Failed to send email to {recipient_email}")
                        except Exception as e:
                            logger.error(f"Error processing supervisor {supervisor}: {str(e)}")
                            failure_count += 1
                    else:
                        logger.warning(f"No valid email extracted for supervisor: {supervisor}")
                        failure_count += 1
                else:
                    logger.info(f"No email needed for {supervisor} (no pending or past due tasks)")
                    
            except Exception as e:
                logger.error(f"Error processing row {index}: {str(e)}")
                failure_count += 1
                continue
        
        return success_count, failure_count
        
    except Exception as e:
        logger.error(f"Error in process_supervisors: {str(e)}")
        return success_count, failure_count



def main(data):  # Modified to accept data parameter
    """
    Process supervisors with provided data instead of loading from file
    """
    process_supervisors(data)


def run_scheduled_job(data=None):  # Modified to optionally accept data
    """
    Run the scheduled job with provided data or wait for upload
    """
    print("Running scheduled job...")
    if data is not None:
        main(data)
        print("Email sent successfully!")
    else:
        print("No data provided for scheduled job")


# Remove the scheduling logic in case of running the script manually or immediately

# Schedule the job to run daily at a specific time
#schedule.every().monday.at("14:45").do(run_scheduled_job)

if __name__ == "__main__":
    print("Script started. Press Ctrl+C to exit.")
    try:
        run_scheduled_job()
        print("Email sending process completed.")
        #while True:
        #    schedule.run_pending()
        #    time.sleep(60)
    except KeyboardInterrupt:
        print("Script stopped by user.")
    