#!/usr/bin/env python3

# The IP file path is where the program will store the IP address. Updates
# to AWS are only sent when the IP address changes.

# export DNS_ADJUSTER_CONFIG="ZONE_ID:example.com|ZONE_ID:example2.com"
# export DNS_ADJUSTER_LOGPATH="/path/to/dns_adjuster.log"
# export DNS_ADJUSTER_IPFILEPATH="/path/to/ip-file-path"
# python dns_updater.py

import os
import boto3
import argparse
import logging
import subprocess
import requests
from datetime import datetime

def setup_logging():
    log_path = os.getenv('DNS_ADJUSTER_LOGPATH')
    if not log_path:
        raise ValueError("DNS_ADJUSTER_LOGPATH environment variable not set")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, mode='a'),
            logging.StreamHandler()  # Also log to console
        ]
    )
    return logging.getLogger(__name__)

def get_external_ip():
    try:
        # Using ipify API - a simple and reliable service
        response = requests.get('https://api.ipify.org')
        return response.text
    except requests.RequestException:
        try:
            # Fallback to another service if first one fails
            response = requests.get('https://ident.me')
            return response.text
        except requests.RequestException:
            return None

def read_stored_ip(filename):
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return f.readline().strip()
        return None
    except Exception as e:
        logging.error(f"Error reading IP from file: {e}")
        return None

def write_ip(filename, ip):
    try:
        with open(filename, 'w') as f:
            f.write(ip)
        return True
    except Exception as e:
        logging.error(f"Error writing IP to file: {e}")
        return False

def update_dns_record(route53_client, zone_id, domain, ip):
    change_batch = {
        'Changes': [
            {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': domain,
                    'Type': 'A',
                    'TTL': 300,
                    'ResourceRecords': [
                        {
                            'Value': ip
                        }
                    ]
                }
            }
        ]
    }

    return route53_client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch=change_batch
    )

def main():
    logger = setup_logging()
    try:
        # Initialize Route53 client
        route53 = boto3.client('route53')

        # Get and parse environment variables
        config = os.getenv('DNS_ADJUSTER_CONFIG', '')
        if not config:
            logger.error("DNS_ADJUSTER_CONFIG environment variable not set")
            return

        ip_file = os.getenv('DNS_ADJUSTER_IPFILEPATH', '')
        if not config:
            logger.error("DNS_ADJUSTER_IPFILEPATH environment variable not set")
            return

        # Get current external IP
        current_ip = get_external_ip()
        if not current_ip:
            return

        # Read stored IP
        stored_ip = read_stored_ip(ip_file)

        # Compare and update if different
        if stored_ip != current_ip:
            # Process each pair
            pairs = config.split('|')
            for pair in pairs:
                if ':' not in pair:
                    logger.warning(f"Skipping invalid pair: {pair}")
                    continue
                zone_id, domain = pair.split(':')
                try:
                    response = update_dns_record(route53, zone_id, domain, current_ip)
                    logger.info(f"Updated {zone_id}:{domain} -> {current_ip}: {response['ChangeInfo']['Id']}")
                    if write_ip(ip_file, current_ip):
                        logging.info(f"IP updated from {stored_ip} to {current_ip}")
                    else:
                        logging.error("Failed to update IP file")
                except Exception as e:
                    logger.error(f"Error updating {zone_id}:{domain} -> {current_ip}: {str(e)}")
        else:
            logging.info("IP unchanged")

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
