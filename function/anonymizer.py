"""Anonymization Lambda function."""
import time
from typing import Tuple
from faker import Faker
from collections import defaultdict
from datetime import datetime, date, timedelta
from aws_lambda_powertools import Logger

import boto3
import requests
import csv
import io

s3 = boto3.client('s3')
logger = Logger()
faker = Faker()
today = date.today()

@logger.inject_lambda_context
def handler(event, context):
    """
    Lambda function handler
    """
    logger.set_correlation_id(event["xAmzRequestId"])
    logger.info('Received event with requestId: %s', event["xAmzRequestId"])
    logger.debug(f'Raw event {event}')

    object_get_context = event["getObjectContext"]
    request_route = object_get_context["outputRoute"]
    request_token = object_get_context["outputToken"]
    s3_url = object_get_context["inputS3Url"]

    # Get original object (not anonymized) from S3
    time1 = time.time()
    original_object = download_file_from_s3(s3_url)
    time2 = time.time()
    logger.debug(f"Downloaded original file in {(time2 - time1)} seconds")

    # Anonymize
    time1 = time.time()
    rows, anonymized_object = anonymize(original_object)
    time2 = time.time()
    logger.debug(f"Anonymized the file ({rows} records) in {(time2 - time1)} seconds")

    # Send response back to requester
    time1 = time.time()
    s3.write_get_object_response(
        Body=anonymized_object,
        RequestRoute=request_route,
        RequestToken=request_token)
    time2 = time.time()
    logger.debug(f"Sending anonymized file in {(time2 - time1)} seconds")

    return {'status_code': 200}


def download_file_from_s3(presigned_url):
    """
    Download the file from a S3's presigned url.
    Python AWS-SDK doesn't provide any method to download from a presigned url directly
    So we have to make a simple GET httpcall using requests.
    """
    logger.debug(f"Downloading object with presigned url {presigned_url}")
    response = requests.get(presigned_url)
    
    if response.status_code != 200:
        logger.error("Failed to download original file from S3")
        raise Exception(f"Failed to download original file from S3, error {response.status_code}")

    return response.content.decode('utf-8-sig')


def filter_columns(reader, keys):
    """
    Select only columns we want to keep in the final result,
    the ones useful for the final client and not containing identifying information
    """
    for r in reader:
        yield dict((k, r[k]) for k in keys)


def anonymize(original_object)-> Tuple[int, str]:
    """
    Read through the original CSV object and perform anonymization:
    - Select only columns we want to keep
    - Perform some pseudonymization on Name / Birthdate
    Write the new CSV object
    """
    logger.debug("Anonymizing object")
    reader = csv.DictReader(io.StringIO(original_object))

    input_selected_fieldnames = ['Fullname', 'Birthdate', 'Gender', 'Smoking', 'Weight', 'Height', 'Disease']
    
    output_selected_fieldnames = input_selected_fieldnames.copy()
    output_selected_fieldnames.remove('Birthdate')
    output_selected_fieldnames.insert(1, 'Age')

    transformed_object = ''
    with io.StringIO() as output:
        writer = csv.DictWriter(output, fieldnames=output_selected_fieldnames, quoting=csv.QUOTE_NONE)
        writer.writeheader()

        rows = 0
        for row in filter_columns(reader, input_selected_fieldnames):
            writer.writerow(pseudonymize_row(row))
            rows += 1

        transformed_object = output.getvalue()
    
    return rows, transformed_object


def pseudonymize_row(row):
    """
    Replace some identifying information with others:
    - Fake name 
    - Birthdate is replaced with the age
    """
    anonymized_row = row.copy()

    # using Faker (https://faker.readthedocs.io/en/master/), we generate fake names
    if anonymized_row['Gender'] == 'Female':
        anonymized_row['Fullname'] = faker.name_female()
    else:
        anonymized_row['Fullname'] = faker.name_male()

    del anonymized_row['Birthdate']
    birthdate = datetime.strptime(row['Birthdate'], '%Y-%m-%d')
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    anonymized_row['Age'] = age

    return anonymized_row
