from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from io import BytesIO
from typing import Optional, Tuple, Dict, List
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
import os
import logging

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
    """
    Generate a visualisation chart for the email.

    Optimising chart generation using data structures:
    - dict: O(1) lookup for supervisor data
    - minimise DataFrame operations to reduce processing time
    - process data in single pass
    """
    try:
        # Get Course Units (2) section
        start_idx, end_idx = get_course_unit_2_indices(data)
        if start_idx is None or end_idx is None:
            raise ValueError("Could not find Course Units (2) section")
            
        # Prepare data for visualisation in a single pass
        chart_data = {}
        max_total = 0

        for idx in range(start_idx, end_idx-3):
            row = data.iloc[idx]
            supervisor = str(row.iloc[0])

            if pd.isna(supervisor) or supervisor.strip() == '':
                continue

            metrics = {
                'Completed': safe_convert_to_float(row.iloc[11]),
                'Pending': safe_convert_to_float(row.iloc[14]),
                'Past Due': safe_convert_to_float(row.iloc[13])
            }

            total = sum(metrics.values())
            max_total = max(max_total, total)
            chart_data[supervisor] = metrics

        sorted_supervisors = sorted(chart_data.keys(), reverse=True)
        
        # Create plot with pre-calculated dimensions
        num_supervisors = len(sorted_supervisors)
        fig_height = max(6, num_supervisors * 0.4)
        fig, ax = plt.subplots(figsize=(12, fig_height))
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        y_positions = range(num_supervisors)
        left_values = [0] * num_supervisors
        colors = ['#2ecc71', '#f1c40f', '#e74c3c']
        categories = ['Completed', 'Pending', 'Past Due']
        
        # Plot bars efficiently
        for category, color in zip(categories, colors):
            values = [chart_data[sup][category] for sup in sorted_supervisors]
            ax.barh(y_positions, values, left=left_values, color=color, label=category)
            left_values = [l + v for l, v in zip(left_values, values)]
        
        ax.set_yticks(y_positions)
        ax.set_yticklabels(sorted_supervisors)
        ax.set_title('Task Status by Supervisor', pad=50)
        ax.legend(bbox_to_anchor=(0.5, 1.02), loc='lower center', ncol=3)
        ax.grid(True, axis='x', linestyle='--', alpha=0.7)
        
        # Add value labels in single pass
        for idx, supervisor in enumerate(sorted_supervisors):
            metrics = chart_data[supervisor]
            text = f"{int(metrics['Completed'])} | {int(metrics['Pending'])} | {int(metrics['Past Due'])}"
            ax.text(max_total * 1.02, idx, text, va='center', ha='left', fontsize=9)
        
        plt.xlim(0, max_total * 1.2)
        ax.axvline(x=max_total, color='gray', linestyle='--', linewidth=0.8)
        plt.tight_layout()
        
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300)
        img_buffer.seek(0)
        plt.close()
        
        return img_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        raise


def format_text_with_line_breaks(text: str) -> str:
    """Convert new lines to HTML paragraphs."""
    return ''.join(f'<p>{line}</p>' for line in text.split('\n') if line.strip())


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
            <h1 style="color: #2c3e50; font-size: 28px; font-weight: bold; margin-bottom: 24px;">{email_template['subject']}</h1>
            {format_text_with_line_breaks(email_template['greeting'])}
            {format_text_with_line_breaks(email_template['intro'])}
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                {metrics_html}
            </div>
            
            {format_text_with_line_breaks(email_template['action'])}
            <img src="cid:task_chart" style="max-width: 100%; height: auto;">
            {format_text_with_line_breaks(email_template['closing'])}
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
        msg['From'] = sender or os.getenv('SMTP_SENDER', '212724071@geaerospace.com')
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
        test_recipient = recipient or os.getenv('ADMIN_EMAIL', '212724071@geaerospace.com')
        logger.info(f"Sending test email to: {test_recipient}")
        
        # Generate content with zero metrics
        content = create_email_content(metrics, template)
        subject = f"[COPY] {template.get('subject', EmailTemplate.DEFAULT_TEMPLATE['subject'])}"
        
        # Send email using existing function
        success = send_email(test_recipient, subject, content, chart)
        if success:
            logger.info(f"Test email successfully sent to {test_recipient}")
        else:
            logger.error(f"Failed to send test email to {test_recipient}")
        return success
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
    
    Optimising performance by using data structures:
    - defaultdict: grouping pending tasks by supervisor
    - pre-calculating metrics and storing in a cache
    - batch process similar operations to reduce duplicate work
    """
    success_count = 0
    failure_count = 0
    
    try:
        # Get Course Units (2) section indices
        start_idx, end_idx = get_course_unit_2_indices(data)
        if start_idx is None or end_idx is None:
            logger.error("Could not find Course Units (2) section")
            return 0, 0
        
        metrics_cache = {}
        supervisor_emails = {}
        pending_tasks = defaultdict(list)

        chart = generate_chart(data)
        
        # Process each supervisor
        for idx in range(start_idx, end_idx-3):
            row = data.iloc[idx]
            supervisor = str(row.iloc[0])
            
            if pd.isna(supervisor) or supervisor.strip() == '':
                continue
            
            metrics = {
                'total': safe_convert_to_float(row.iloc[10]),
                'completed': safe_convert_to_float(row.iloc[11]),
                'past_due': safe_convert_to_float(row.iloc[13]),
                'pending': safe_convert_to_float(row.iloc[14])
            }
            
            # Calculate completion rate and store in cache
            metrics['completion_rate'] = (metrics['completed'] / metrics['total'] * 100) if metrics['total'] > 0 else 0
            metrics_cache[supervisor] = metrics

            email = extract_sso_id(supervisor)
            if email:
                supervisor_emails[supervisor] = email
            
            # Check if email needed
            if metrics['pending'] > 0 or metrics['past_due'] > 0:
                pending_tasks[supervisor].append(idx)

        for supervisor in pending_tasks:
            if supervisor not in supervisor_emails:
                failure_count += 1
                continue

            try:
                email = supervisor_emails[supervisor]
                metrics = metrics_cache[supervisor]
                
                content = create_email_content(metrics, email_template)
                subject = email_template.get('subject', EmailTemplate.DEFAULT_TEMPLATE['subject']) if email_template else EmailTemplate.DEFAULT_TEMPLATE['subject']
                
                if send_email(email, subject, content, chart):
                    success_count += 1
                    logger.info(f"Successfully processed supervisor: {supervisor}")
                else:
                    failure_count += 1
                    logger.error(f"Failed to send email to supervisor: {supervisor}")
                        
            except Exception as e:
                logger.error(f"Error processing supervisor {supervisor}: {str(e)}")
                failure_count += 1
                
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


if __name__ == "__main__":
    try:
        print("Script started. Press Ctrl+C to exit.")
        run_scheduled_job()
        print("Email sending process completed.")
    except KeyboardInterrupt:
        print("Script stopped by user.")
    except Exception as e:
        print(f"Script execution failed: {str(e)}")