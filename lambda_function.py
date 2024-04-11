import os
import json
import csv
import boto3
import pandas as pd
import tempfile  
import re
from datetime import datetime

s3 = boto3.client('s3')

# Function to extract and format date from filename
def extract_date(filename):
    match = re.search(r'\d{4}-\d{2}-\d{2}', filename)
    
    if match:
        date_str = match.group()
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%Y-%m-%d')
        return formatted_date
    else:
        return None

# Function to download JSON files from S3 bucket
def download_json_files(bucket_name, folder_prefix, temp_dir):
    file_keys = []
    paginator = s3.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=bucket_name, Prefix=folder_prefix):
        for obj in page.get('Contents', []):
            full_file_name = obj["Key"].split("/")[-1]
            file_name = os.path.join(temp_dir, full_file_name)
            s3.download_file(bucket_name, obj['Key'], file_name)
            file_keys.append(full_file_name)

    return [os.path.join(temp_dir, key) for key in file_keys]

# Function to flatten JSON data
def flatten_json(y):
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out

# Function to convert JSON files to CSV
def json_to_csv(json_files, csv_file):
    with open(csv_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        header_written = False
        for json_file in json_files:
            with open(json_file, 'r') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, dict):
                        file_date = extract_date(json_file) 
                        if file_date:
                            common_keys = ['version', 'assessment_type', 'input_note', 'output_note']
                            selected_values = [data.get(key, 'N/A') for key in common_keys]
                            if not header_written:
                                csv_writer.writerow(['Date'] + common_keys)
                                header_written = True
                            csv_writer.writerow([file_date] + selected_values)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON file '{json_file}': {e}")


    print(f"CSV file '{csv_file}' created successfully.")

# Function to upload CSV file to S3 bucket
def upload_csv_to_s3(csv_file, bucket_name, folder_prefix):
    s3.upload_file(csv_file, bucket_name, f"{folder_prefix}/{os.path.basename(csv_file)}")

# Lambda handler function
def lambda_handler(event, context):
    source_bucket_name = 'dev-app-logging'
    source_folder_prefix = 'msf-report/default_logs/'
    destination_bucket_name = 'dev-app-logging'
    destination_folder_prefix = 'msf-report/msf_logs_csv/'
    
    temp_dir = tempfile.mkdtemp()
    json_files = download_json_files(source_bucket_name, source_folder_prefix, temp_dir)
    csv_file = os.path.join(temp_dir, 'output.csv')
    json_to_csv(json_files, csv_file)
    
    # Upload CSV file to another S3 bucket
    upload_csv_to_s3(csv_file, destination_bucket_name, destination_folder_prefix)

    return {
        'statusCode': 200,
        'body': json.dumps('CSV file created and uploaded successfully.')
    }
