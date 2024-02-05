import boto3
import datetime
import pandas as pd
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pytz

def get_instance_ids():
    # Read and parse the 'INSTANCES' environment variable
    instances_env = os.environ.get('INSTANCES', '')
    return [instance.strip() for instance in instances_env.split(',') if instance.strip()]

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    cloudwatch = boto3.client('cloudwatch')
    ses = boto3.client('ses')

    # Define the time zone (IST)
    ist = pytz.timezone('Asia/Kolkata')

    # Define the time range for the report (last 24 hours) in IST
    end_time = datetime.datetime.now(ist)
    start_time = end_time - datetime.timedelta(days=1)

    # Format the time range for inclusion in the table (IST)
    time_range = f"{start_time.strftime('%Y-%m-%d %H:%M:%S %Z')} - {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"

    # Query CPU utilization metrics for instances specified in the environment variable
    metric_name = 'CPUUtilization'
    namespace = 'AWS/EC2'
    period = 3600  # 1 hour resolution

    # Get instance IDs from the environment variable
    instances = get_instance_ids()

    instance_data = []

    for instance_id in instances:
        instance = ec2.describe_instances(InstanceIds=[instance_id])
        instance_name = None

        if 'Tags' in instance['Reservations'][0]['Instances'][0]:
            for tag in instance['Reservations'][0]['Instances'][0]['Tags']:
                if tag['Key'] == 'Name':
                    instance_name = tag['Value']
                    break

        response = cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'm1',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': namespace,
                            'MetricName': metric_name,
                            'Dimensions': [
                                {
                                    'Name': 'InstanceId',
                                    'Value': instance_id
                                },
                            ]
                        },
                        'Period': period,
                        'Stat': 'Maximum',
                    },
                    'ReturnData': True,
                },
                {
                    'Id': 'm2',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': namespace,
                            'MetricName': metric_name,
                            'Dimensions': [
                                {
                                    'Name': 'InstanceId',
                                    'Value': instance_id
                                },
                            ]
                        },
                        'Period': period,
                        'Stat': 'Minimum',
                    },
                    'ReturnData': True,
                },
                {
                    'Id': 'm3',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': namespace,
                            'MetricName': metric_name,
                            'Dimensions': [
                                {
                                    'Name': 'InstanceId',
                                    'Value': instance_id
                                },
                            ]
                        },
                        'Period': period,
                        'Stat': 'Average',
                    },
                    'ReturnData': True,
                },
            ],
            StartTime=start_time,
            EndTime=end_time,
        )

        if 'Values' in response['MetricDataResults'][0]:
            max_cpu = max(response['MetricDataResults'][0]['Values'])
            min_cpu = min(response['MetricDataResults'][1]['Values'])
            avg_cpu = sum(response['MetricDataResults'][2]['Values']) / len(response['MetricDataResults'][2]['Values'])

            instance_data.append({
                'Instance ID': instance_id,
                'Instance Name': instance_name,
                'Max CPU Utilization': max_cpu,
                'Min CPU Utilization': min_cpu,
                'Avg CPU Utilization': avg_cpu,
                'Time Range': time_range
            })

    # Create a DataFrame with instance data
    df = pd.DataFrame(instance_data)

    # Sort the DataFrame by Max CPU Utilization in descending order while keeping the order of instances
    df = df[df['Instance ID'].isin(instances)]
    
    # Create an HTML table from the DataFrame with light-colored styling
    html_table = df.to_html(index=False, classes='table table-bordered table-striped', escape=False)

    # Add CSS styles for a light-colored table
    html_table = html_table.replace('<table border="1" class="dataframe table table-bordered table-striped">',
                                    '<table style="border-collapse: collapse; width: 100%; max-width: 800px; margin: 0 auto; background-color: #f5f5f5; border: 1px solid #ddd; text-align: left;">')
    html_table = html_table.replace('<th>', '<th style="background-color: #f0f0f0; padding: 8px; border: 1px solid #ddd;">')
    html_table = html_table.replace('<td>', '<td style="padding: 8px; border: 1px solid #ddd;">')

    # Email configuration
    sender_email = os.environ['SENDER_EMAIL']
    receiver_emails = os.environ['RECEIVER_EMAILS'].split(',')
    subject = 'North Virginia CPU Utilization Report'

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