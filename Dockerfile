# Use Python 3 base image
FROM python:3-slim

# Install cron and required packages
RUN apt-get update && \
    apt-get install -y cron && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir boto3 requests

# Create directory for the script
WORKDIR /app

# Add the Python script
COPY check-and-update-ip.py .

# Add AWS CLI for credential handling
RUN apt-get update && \
    apt-get install -y cron curl unzip && \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* awscliv2.zip aws

# Modify the start-cron.sh script to include credential checking
RUN echo '#!/bin/sh\n\
# Check for AWS credentials\n\
if [ -n "${AWS_WEB_IDENTITY_TOKEN_FILE}" ]; then\n\
    echo "Using IAM role authentication"\n\
elif [ -n "${AWS_ACCESS_KEY_ID}" ] && [ -n "${AWS_SECRET_ACCESS_KEY}" ]; then\n\
    echo "Using environment variable authentication"\n\
elif [ -d "/root/.aws" ]; then\n\
    echo "Using mounted AWS credentials"\n\
else\n\
    echo "No AWS credentials found. Please provide credentials via environment variables, mounted ~/.aws directory, or IAM role."\n\
    exit 1\n\
fi\n\
\n\
# Export all environment variables to a file\n\
env > /etc/environment\n\
\n\
CRON_SCHEDULE="${DNS_ADJUSTER_CRONJOB}"\n\
echo "${CRON_SCHEDULE} . /etc/environment && /usr/local/bin/python /app/check-and-update-ip.py >> /var/log/cron.log 2>&1" > /etc/cron.d/dns-adjuster\n\
chmod 0644 /etc/cron.d/dns-adjuster\n\
crontab /etc/cron.d/dns-adjuster\n\
touch /var/log/cron.log\n\
    cron -f' > /app/start-cron.sh

# Make the script executable
RUN chmod +x /app/start-cron.sh

# Create log file
RUN touch /var/log/cron.log

# Set entrypoint
ENTRYPOINT ["/app/start-cron.sh"]
