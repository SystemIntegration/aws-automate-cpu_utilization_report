import boto3
import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pytz  # Import the pytz library


# AWS credentials and region
aws_access_key_id = '***************'
aws_secret_access_key = '*******************'
aws_region = '******'

# Initialize AWS clients
cloudwatch = boto3.client('cloudwatch', region_name=aws_region)
ec2 = boto3.client('ec2', region_name=aws_region)
ses = boto3.client('ses', region_name=aws_region)
# Define the time zone (IST)
ist = pytz.timezone('Asia/Kolkata')

# Define the time range for the report (last 24 hours) in IST
end_time = datetime.datetime.now(ist)  # Current time in IST
start_time = end_time - datetime.timedelta(days=1)

# Format the time range for inclusion in the table (IST)
time_range = f"{start_time.strftime('%Y-%m-%d %H:%M:%S %Z')} - {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"

# Query CPU utilization metrics for all EC2 instances
metric_name = 'CPUUtilization'
namespace = 'AWS/EC2'
period = 3600  # 1 hour resolution
instances = ['i-232323,i-1212211']  # Replace with your instance IDs

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
                    'Stat': 'Maximum',  # Maximum value over the period
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
                    'Stat': 'Minimum',  # Minimum value over the period
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
                    'Stat': 'Average',  # Average value over the period
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

# Sort by Max CPU Utilization in descending order
#df = df.sort_values(by='Max CPU Utilization', ascending=False)

# Sort the DataFrame by Max CPU Utilization in descending order while keeping the order of instances
df = df[df['Instance ID'].isin(instances)]
#df = df.sort_values(by='instances', ascending=False)



# Create an HTML table from the DataFrame with light-colored styling
html_table = df.to_html(index=False, classes='table table-bordered table-striped', escape=False)




# Add CSS styles for a light-colored table
html_table = html_table.replace('<table border="1" class="dataframe table table-bordered table-striped">', '<table style="border-collapse: collapse; width: 100%; max-width: 800px; margin: 0 auto; background-color: #f5f5f5; border: 1px solid #ddd; text-align: left;">')
html_table = html_table.replace('<th>', '<th style="background-color: #f0f0f0; padding: 8px; border: 1px solid #ddd;">')
html_table = html_table.replace('<td>', '<td style="padding: 8px; border: 1px solid #ddd;">')




# Email configuration
sender_email = 'YOUR_SENDER_EMAIL'  # Use a verified email address in SES
receiver_emails = ['YOUR_RECEIVER_EMAIL']  # Add your receiver email addresses
subject = 'EC2 CPU Utilization Report'



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
    print(f"Report sent successfully to {', '.join(receiver_emails)}")
except Exception as e:
    print(f"Error sending email: {str(e)}")
