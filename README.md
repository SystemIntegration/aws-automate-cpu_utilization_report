# AWS Lambda CPU Utilization Report

## Overview

This repository contains an AWS Lambda function designed to fetch daily CPU utilization metrics from AWS CloudWatch and send an email report via AWS SES.

## Features

- **Automated Reporting**: Fetches CPU utilization metrics automatically on a daily basis.
- **Email Integration**: Sends reports via AWS SES to designated recipients.
- **Customizable**: Easily configurable environment variables for flexible usage.
- **Monitoring**: Monitors Lambda execution and CloudWatch Logs for detailed insights.

## Prerequisites

Before getting started, ensure you have the following:

- An AWS account with permissions to create and manage Lambda functions, CloudWatch, SES, and EventBridge.
- Python and pip installed on your local machine for development.
- Basic knowledge of AWS services and Python programming.

## Usage

1. **Clone the Repository:**
    ```bash
    git clone https://github.com/your_username/aws-cpu-utilization-report.git
    cd aws-cpu-utilization-report
    ```

2. **Install Required Packages:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Update Environment Variables:**
    Update the following environment variables in the Lambda function with your specific configuration:
    
    - `RECEIVER_EMAILS`: Email addresses where reports will be sent.
    - `INSTANCES`: AWS EC2 instances for which CPU utilization metrics will be fetched.
    - `SENDER_EMAIL`: Email address used to send reports.

4. **Deploy Lambda Function:**
    - Zip the contents of the project:
    
    ```bash
    zip -r lambda_function.zip .
    ```
    
    - Create a Lambda function in the AWS Management Console and upload `lambda_function.zip`.

5. **Set Up EventBridge Rule for Scheduling:**
    - Go to EventBridge in the AWS Management Console.
    - Create a new rule with the desired schedule (e.g., daily at 8 AM).
    - Configure the rule to trigger the Lambda function.

6. **Monitor Lambda Execution:**
    - Keep an eye on Lambda function executions in the AWS Lambda console.
    - Check CloudWatch Logs for detailed logs of each execution.

## Additional Information

- **Cost Considerations**: Be mindful of AWS costs associated with Lambda invocations, CloudWatch metrics, and SES usage.
- **Security**: Ensure proper IAM roles and permissions are set up for the Lambda function to access CloudWatch and SES.
- **Error Handling**: Implement robust error handling and logging within the Lambda function to handle potential issues gracefully.
- **Feedback and Contributions**: Contributions and feedback are welcome! Feel free to submit pull requests or open issues.

## License

This project is licensed under the [MIT License](LICENSE).

