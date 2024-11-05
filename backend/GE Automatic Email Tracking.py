import pandas as pd
import matplotlib.pyplot as plt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib
import schedule
import time
from io import BytesIO
import socket

def load_data(file_path):
    return pd.read_csv(file_path, skiprows=1)


def get_course_unit_2_indices(data):
    """Find the start and end indices for Course Unit (2) section"""
    course_unit_2_start = None
    course_unit_2_end = None
    
    for idx, row in data.iterrows():
        if 'Course Unit (2)' in str(row.iloc[0]):
            course_unit_2_start = idx + 1  # Start from next row
        elif course_unit_2_start is not None and pd.isna(row.iloc[0]):
            course_unit_2_end = idx
            break
    
    return course_unit_2_start, course_unit_2_end


def generate_chart(data):
    # Read the CSV data and remove the last two rows
    data = load_data('Testing Data.csv')
    data = data.iloc[:-3]  # Remove the last three rows which contain notes and totals
    start_idx, end_idx = get_course_unit_2_indices(data)
    data = data.iloc[start_idx:end_idx] # Extract only Course Unit (2) data

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


def extract_ssoID(supervisor_string):
    try:
        if '[' in supervisor_string and ']' in supervisor_string:
            sso_id = supervisor_string.split('[')[-1].strip(']')
            return f"{sso_id}@ge.com"
        else:
            print(f"No SSO ID found in string: {supervisor_string}")
            return None
    except Exception as e:
        print(f"Error extracting SSO ID from {supervisor_string}: {str(e)}")
        return None


def send_email(recipient, subject, body, chart):
    msg = MIMEMultipart()
    msg['From'] = "223144086@ge.com"
    msg['To'] = recipient
    msg['Subject'] = subject

    # Create the email content
    msg.attach(MIMEText(body, 'html'))

    # Attach the chart image
    img = MIMEImage(chart)
    img.add_header('Content-ID', '<task_chart>')
    msg.attach(img)

    # SMTP Configuration
    smtp_server = "e2ksmtp01.e2k.ad.ge.com"
    smtp_port = 25  # Standard SMTP port

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()  # Say hello to the server
            
            # Only start TLS if supported
            try:
                server.starttls()
                server.ehlo()  # Say hello again after TLS
            except smtplib.SMTPNotSupportedError:
                print("TLS not supported by server, continuing without encryption")
            except Exception as e:
                print(f"TLS error: {str(e)}, continuing without encryption")
            
            # Send without authentication
            server.send_message(msg)
            print(f"Email sent successfully to {recipient}")

    except socket.gaierror as e:
        print(f"Failed to resolve SMTP server hostname. Error: {str(e)}")
        print("Please check your SMTP server configuration and network connection.")
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred. Error: {str(e)}")
    except Exception as e:
        print(f"Failed to send email to {recipient}. Error: {str(e)}")


def process_supervisors(data):
    start_idx, end_idx = get_course_unit_2_indices(data)
    course_unit_2_data = data.iloc[start_idx:end_idx]
    
    for index, row in course_unit_2_data.iterrows():
        supervisor = row.iloc[0]
        pending = pd.to_numeric(row.iloc[14], errors='coerce')
        past_due = pd.to_numeric(row.iloc[13], errors='coerce')

        if (pd.notna(row.get('Pending')) and row.get('Pending', 0) > 0) or (pd.notna(row.get('Past Due')) and row.get('Past Due', 0) > 0):
            recipient_email = "223144086@ge.com" #extract_ssoID(supervisor)
            if recipient_email:
                chart = generate_chart(data)
                row_data = pd.Series({
                    'Total': pd.to_numeric(row.iloc[10], errors='coerce'),
                    'Completion': pd.to_numeric(row.iloc[11], errors='coerce'),
                    'Past Due': past_due,
                    'Pending': pending
                })
                email_content = create_email_content(row_data)
                send_email(recipient_email, "Ignore it", email_content, chart)


def main():
    data = load_data('Testing Data.csv')
    process_supervisors(data)


def run_scheduled_job():
    print("Running scheduled job...")
    main()
    print("Email sent successfully!")


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
    