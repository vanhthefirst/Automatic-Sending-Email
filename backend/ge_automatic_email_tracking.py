from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from io import BytesIO
from typing import Optional, Tuple, Dict, Union
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
import schedule
import time
import os
import socket
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='email_tracking.log'
)
logger = logging.getLogger(__name__)

class EmailTemplate:
    """Default email template content."""
    DEFAULT_TEMPLATE = {
        "subject": "Training Tasks Update",
        "greeting": "Dear Team Leader,",
        "intro": "This is a reminder about pending training tasks in your team:",
        "action": "Please ensure your team completes any pending or past due tasks by this Friday.\nBelow is the chart to show the current status of your team and others:",
        "closing": "Best regards,\nHR Team"
    }


def get_course_unit_2_indices(data: pd.DataFrame) -> Tuple[Optional[int], Optional[int]]:
    """Find the start and end indices for Course Units (2) section."""
    try:
        start_idx = 1
        end_idx = len(data)
        
        if start_idx is None:
            logger.error("Could not find Course Units (2) section")
            return None, None
        
        # If we didn't find an end, use the last row
        if end_idx is None:
            end_idx = len(data)
            
        return start_idx, end_idx
        
    except Exception as e:
        logger.error(f"Error finding Course Units (2) indices: {str(e)}")
        return None, None


def safe_convert_to_float(value: any) -> float:
    """Safely convert any value to float, returning 0.0 if conversion fails."""
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def extract_sso_id(supervisor: str) -> Optional[str]:
    """Extract SSO ID from supervisor string and return email address."""
    try:
        if pd.isna(supervisor) or not isinstance(supervisor, str):
            return None
        if '[' in supervisor and ']' in supervisor:
            sso_id = supervisor.split('[')[-1].strip(']').strip()
            return f"{sso_id}@geaerospace.com"
        return None
    except Exception as e:
        logger.error(f"Error extracting SSO ID from '{supervisor}': {str(e)}")
        return None


def generate_chart(data: pd.DataFrame) -> bytes:
    """Generate a visualisation chart for the email."""
    try:
        # Get Course Units (2) section
        start_idx, end_idx = get_course_unit_2_indices(data)
        if start_idx is None or end_idx is None:
            raise ValueError("Could not find Course Units (2) section")
            
        # Prepare data for visualisation
        chart_data = []
        for idx in range(start_idx, end_idx-3):
            row = data.iloc[idx]
            supervisor = str(row.iloc[0])
            if pd.isna(supervisor) or supervisor.strip() == '':
                continue
                
            chart_data.append({
                'Supervisor': supervisor,
                'Completed': safe_convert_to_float(row.iloc[11]),
                'Pending': safe_convert_to_float(row.iloc[14]),
                'Past Due': safe_convert_to_float(row.iloc[13])
            })
        
        df_chart = pd.DataFrame(chart_data)
        df_chart = df_chart.sort_values('Supervisor', ascending=False)
        
        # Create the chart
        fig, ax = plt.subplots(figsize=(12, max(6, len(df_chart) * 0.4)))

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Plot stacked bars
        left_values = pd.Series(0, index=df_chart.index)
        colors = ['#2ecc71', '#f1c40f', '#e74c3c']  # Green, Yellow, Red
        labels = ['Completed', 'Pending', 'Past Due']
        
        bars = []
        for column, color, label in zip(['Completed', 'Pending', 'Past Due'], colors, labels):
            bar = ax.barh(range(len(df_chart)), df_chart[column], left=left_values, 
                         color=color, label=label)
            bars.append(bar)
            left_values += df_chart[column]
        
        ax.set_yticks(range(len(df_chart)))
        ax.set_yticklabels(df_chart['Supervisor'])

        total_width = df_chart[['Completed', 'Pending', 'Past Due']].sum(axis=1).max()

        # Customise chart
        ax.set_title('Task Status by Supervisor', pad=50)
        ax.legend(bbox_to_anchor=(0.5, 1.02), loc='lower center', ncol=3)
        ax.grid(True, axis='x', linestyle='--', alpha=0.7)
        for idx, row in df_chart.iterrows():
            y_pos = list(df_chart.index).index(idx) # Get the correct y position after sorting
            text = f"{int(row['Completed'])} | {int(row['Pending'])} | {int(row['Past Due'])}"
            ax.text(total_width * 1.02, y_pos, text, va='center', ha='left', fontsize=9)
        
        plt.xlim(0, total_width * 1.2)
        ax.axvline(x=total_width, color='gray', linestyle='--', linewidth=0.8) # Vertical line to separate chart from labels
        plt.tight_layout()
        
        # Save to bytes
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300)
        img_buffer.seek(0)
        plt.close()
        
        return img_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        raise


def create_email_content(
    data: Dict[str, float],
    template: Optional[Dict[str, str]] = None
) -> str:
    """
    Create HTML email content with a customisable template.
    
    Args:
        data: Dictionary containing metrics (total, completed, pending, past_due, completion_rate)
        template: Dictionary containing email template parts (subject, greeting, intro, action, closing)
    """
    try:
        # Use provided template or default
        email_template = template or EmailTemplate.DEFAULT_TEMPLATE
        
        # Create metrics HTML section
        metrics_html = f"""
            <p><strong>Total Tasks:</strong> {int(data['total'])}</p>
            <p><strong>Completed:</strong> {int(data['completed'])} ({data['completion_rate']:.2f}%)</p>
            <p><strong>Pending:</strong> {int(data['pending'])}</p>
            <p><strong>Past Due:</strong> {int(data['past_due'])}</p>
        """
        
        # Full HTML template with custom styling
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">{email_template['subject']}</h2>
            <p>{email_template['greeting']}</p>
            <p>{email_template['intro']}</p>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                {metrics_html}
            </div>
            
            <p>{email_template['action']}</p>
            <p>The chart below shows the current status of your team and others:</p>
            <img src="cid:task_chart" style="max-width: 100%; height: auto;">
            
            <p style="margin-top: 20px;">{email_template['closing']}</p>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error creating email content: {str(e)}")
        raise


# Test without actual email sending
# DEV_MODE = os.getenv('DEV_MODE', 'False').lower() == 'true'


def send_email(
    recipient: str,
    subject: str,
    content: str,
    chart: bytes,
    sender: Optional[str] = None
) -> bool:
    """Send email with chart attachment."""
    try:
        msg = MIMEMultipart()
        msg['From'] = sender or os.getenv('SMTP_SENDER', '223144086@geaerospace.com')
        msg['To'] = recipient
        msg['Subject'] = subject
        
        # Attach HTML content
        msg.attach(MIMEText(content, 'html'))
        
        # Attach chart
        img = MIMEImage(chart)
        img.add_header('Content-ID', '<task_chart>')
        msg.attach(img)
        
        # Send email
        with smtplib.SMTP(os.getenv('SMTP_SERVER', 'e2ksmtp01.e2k.ad.ge.com'), 25) as server:
            server.send_message(msg)
            logger.info(f"Email sent successfully to {recipient}")
            return True
    except smtplib.SMTPException as smtp_err:
            logger.error(f"SMTP Error: {str(smtp_err)}")
            return False
    except TimeoutError:
            logger.error("SMTP server connection timeout")
            return False        
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {str(e)}")
        return False
    

def send_test_email(
    template: Dict[str, str],
    metrics: Dict[str, float],
    chart: bytes,
    recipient: Optional[str] = None
) -> bool:
    """Send test email with template data."""
    try:
        # Use default recipient if none provided
        test_recipient = recipient or os.getenv('ADMIN_EMAIL', '223144086@geaerospace.com')
        
        # Generate content with zero metrics
        content = create_email_content(metrics, template)
        subject = f"[TEST] {template.get('subject', EmailTemplate.DEFAULT_TEMPLATE['subject'])}"
        
        # Send email using existing function
        return send_email(test_recipient, subject, content, chart)
    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}")
        return False


def process_supervisors(
    data: pd.DataFrame,
    email_template: Optional[Dict[str, str]] = None,
    send_test: bool = False
) -> Tuple[int, int]:
    """
    Process supervisor data and send emails.
    
    Args:
        data: DataFrame containing supervisor data
        email_template: Optional dictionary containing email template customization
    """
    success_count = 0
    failure_count = 0
    
    try:
        # Get Course Units (2) section indices
        start_idx, end_idx = get_course_unit_2_indices(data)
        if start_idx is None or end_idx is None:
            logger.error("Could not find Course Units (2) section")
            return 0, 0
        
        # Generate chart once for all emails
        chart = generate_chart(data)
        
        # Send test email if requested
        if send_test:
            test_metrics = {
                'total': 0,
                'completed': 0,
                'past_due': 0,
                'pending': 0,
                'completion_rate': 0
            }
            if send_test_email(email_template, test_metrics, chart):
                success_count += 1
                logger.info("Test email sent successfully")
            else:
                failure_count += 1
                logger.error("Failed to send test email")

        # Process each supervisor
        for idx in range(start_idx, end_idx-3):
            row = data.iloc[idx]
            supervisor = str(row.iloc[0])
            
            if pd.isna(supervisor) or supervisor.strip() == '':
                continue
            
            try:
                # Extract metrics
                metrics = {
                    'total': safe_convert_to_float(row.iloc[10]),
                    'completed': safe_convert_to_float(row.iloc[11]),
                    'past_due': safe_convert_to_float(row.iloc[13]),
                    'pending': safe_convert_to_float(row.iloc[14])
                }
                
                # Calculate completion rate
                metrics['completion_rate'] = (metrics['completed'] / metrics['total'] * 100) if metrics['total'] > 0 else 0
                
                # Check if email needed
                if metrics['pending'] > 0 or metrics['past_due'] > 0:
                    email = extract_sso_id(supervisor) # "223144086@geaerospace.com"
                    if email:
                        # Generate email content with template
                        content = create_email_content(metrics, email_template)
                        subject = email_template.get('subject', EmailTemplate.DEFAULT_TEMPLATE['subject']) if email_template else EmailTemplate.DEFAULT_TEMPLATE['subject']
                        
                        # Send email
                        if send_email(email, subject, content, chart):
                            success_count += 1
                            logger.info(f"Successfully processed supervisor: {supervisor}")
                        else:
                            failure_count += 1
                            logger.error(f"Failed to send email to supervisor: {supervisor}")
                    else:
                        logger.warning(f"No valid email for supervisor: {supervisor}")
                        failure_count += 1
                        
            except Exception as e:
                logger.error(f"Error processing supervisor {supervisor}: {str(e)}")
                failure_count += 1
                continue
                
    except Exception as e:
        logger.error(f"Error in process_supervisors: {str(e)}")
        
    return success_count, failure_count


def main(data):
    try:
        if data is not None:
            success_count, failure_count = process_supervisors(data)
            logger.info(f"Email processing complete. Successes: {success_count}, Failures: {failure_count}")
            return success_count, failure_count
        else:
            logger.warning("No data provided to main function")
            return 0, 0
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 0, 0
    

def run_scheduled_job(data: Optional[pd.DataFrame] = None) -> Tuple[int, int]:
    """Run the email processing job."""
    try:
        logger.info("Starting scheduled job...")
        if data is not None:
            success_count, failure_count = process_supervisors(data)
            logger.info(f"Scheduled job completed. Successes: {success_count}, Failures: {failure_count}")
            return success_count, failure_count
        else:
            logger.warning("No data provided for scheduled job")
            return 0, 0
    except Exception as e:
        logger.error(f"Error in scheduled job: {str(e)}")
        return 0, 0


# Remove the scheduling logic in case of running the script manually or immediately
# Schedule the job to run daily at a specific time
#schedule.every().monday.at("14:45").do(run_scheduled_job)


if __name__ == "__main__":
    try:
        print("Script started. Press Ctrl+C to exit.")
        run_scheduled_job()
        #while True:
        #    schedule.run_pending()
        #    time.sleep(60)
        print("Email sending process completed.")
    except KeyboardInterrupt:
        print("Script stopped by user.")
    except Exception as e:
        print(f"Script execution failed: {str(e)}")