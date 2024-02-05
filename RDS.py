import boto3
import datetime
import pandas as pd
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pytz

def get_rds_instance_ids():
    # Read and parse the 'RDS_INSTANCES' environment variable
    rds_instances_env = os.environ.get('RDS_INSTANCES', '')
    return [instance.strip() for instance in rds_instances_env.split(',') if instance.strip()]

def bytes_to_gb(bytes_value):
    return bytes_value / (10**9)  # Convert bytes to gigabytes (1 GB = 10^9 bytes)

def bytes_to_mb(bytes_value):
    return bytes_value / (1024 ** 2)  # Convert bytes to megabytes

def lambda_handler(event, context):
    rds = boto3.client('rds')
    cloudwatch = boto3.client('cloudwatch')
    ses = boto3.client('ses')

    # Define the time zone (IST)
    ist = pytz.timezone('Asia/Kolkata')

    # Define the time range for the report (last 24 hours) in IST
    end_time = datetime.datetime.now(ist)
    start_time = end_time - datetime.timedelta(days=1)

    # Format the time range for inclusion in the table (IST)
    time_range = f"{start_time.strftime('%Y-%m-%d %H:%M %Z')} - {end_time.strftime('%Y-%m-%d %H:%M %Z')}"

    # Query RDS metrics for RDS instances specified in the environment variable
    rds_metric_names = ['CPUUtilization', 'DatabaseConnections', 'FreeStorageSpace', 'FreeableMemory', 'WriteIOPS', 'ReadIOPS']
    rds_namespace = 'AWS/RDS'
    rds_period = 3600  # 1-hour resolution

    rds_instances = get_rds_instance_ids()
    rds_data = []

    for rds_instance_id in rds_instances:
        for metric_name in rds_metric_names:
            response = cloudwatch.get_metric_data(
                MetricDataQueries=[
                    {
                        'Id': 'm1',
                        'MetricStat': {
                            'Metric': {
                                'Namespace': rds_namespace,
                                'MetricName': metric_name,
                                'Dimensions': [
                                    {
                                        'Name': 'DBInstanceIdentifier',
                                        'Value': rds_instance_id
                                    },
                                ]
                            },
                            'Period': rds_period,
                            'Stat': 'Maximum',
                        },
                        'ReturnData': True,
                    },
                ],
                StartTime=start_time,
                EndTime=end_time,
            )

            try:
                max_metric = max(response['MetricDataResults'][0]['Values'])
            except ValueError:
                max_metric = None

            # Perform unit conversion for specific metrics
            if metric_name == 'CPUUtilization':
                max_metric = f"{max_metric:.2f}%"
            elif metric_name == 'FreeStorageSpace':
                max_metric = f"{bytes_to_gb(max_metric):.2f} GB"
            elif metric_name == 'FreeableMemory':
                max_metric = f"{bytes_to_mb(max_metric):.2f} MB"

            rds_data.append({
                'RDS Instance ID': rds_instance_id,
                'Metric Name': metric_name,
                'Max Metric Value': max_metric,
                'Time Range': time_range
            })

    # Create a DataFrame for RDS instance data
    rds_df = pd.DataFrame(rds_data)

    # Create an HTML table from the DataFrame with improved styling
    html_table = rds_df.to_html(index=False, classes='table table-bordered table-striped', escape=False, table_id='rds-max-utilization-table')

    # Add CSS styles for a better table format and design
    html_table = html_table.replace('<table border="1" class="dataframe table table-bordered table-striped">',
                                    '<table style="border-collapse: collapse; width: 100%; max-width: 800px; margin: 0 auto; background-color: #f5f5f5; border: 1px solid #ddd; text-align: left; border-spacing: 0;">')
    html_table = html_table.replace('<th>', '<th style="background-color: #f0f0f0; padding: 8px; border: 1px solid #ddd;">')
    html_table = html_table.replace('<td>', '<td style="padding: 8px; border: 1px solid #ddd;">')

    # Email configuration
    sender_email = os.environ['SENDER_EMAIL']
    receiver_emails = os.environ['RECEIVER_EMAILS'].split(',')
    subject = 'Urban RDS Max Resource Utilization Report (us-east-1)'

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ', '.join(receiver_emails)
    msg['Subject'] = subject
    body = f'<h2>{subject}</h2><br><p>Time Range: {time_range}</p><br>{html_table}'
    msg.attach(MIMEText(body, 'html'))

    # Send the email using SES
    try:
        ses.send_raw_email(
            Source=sender_email,
            Destinations=receiver_emails,
            RawMessage={'Data': msg.as_string()}
        )
        return {
            'statusCode': 200,
            'body': f"Report sent successfully to {', '.join(receiver_emails)}"
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f"Error sending email: {str(e)}"
        }

