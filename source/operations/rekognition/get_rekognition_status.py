import os
import boto3
import urllib3
import json

region = os.environ['AWS_REGION']
transcribe = boto3.client("rekognition")

def lambda_handler(event, context):

    return {"status": "Complete"}
