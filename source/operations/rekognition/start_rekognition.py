###############################################################################
# PURPOSE:
#   Lambda function to perform Rekognition tasks on image and video files
#
# SAMPLE INPUT:
# {
#     "metadata": {},
#     "configuration": {
#         "%%OPERATOR_NAME%%": {
#
#         }
#     },
#     "workflow_execution_id": "%%SOME_WORKFLOW_ID%%",
#     "asset_id": "%%SOME_ASSET_ID%%",
#     "name": "%%OPERATOR_NAME%%",
#     "metrics": {},
#     "status": "%%SOME_VALID_STATUS%%",
#     "input": {
#         "metadata": {},
#         "media": {
#             "file": {
#                 "s3bucket": "ianwow",
#                 "s3key": "hockey.mp4"
#             }
#         }
#     }
# }
#
# SAMPLE DEPLOY:
#   cd source/operations/rekognition/
#   zip start_rekognition.zip start_rekognition.py; aws s3 cp start_rekognition.zip s3://ianwow/
#   cd ../../../deployment
#   aws cloudformation delete-stack --stack-name iantest01
#   aws cloudformation create-stack --stack-name iantest02 --template-body file://rekognition.yaml --capabilities CAPABILITY_IAM
#
# SAMPLE USAGE:
#     FUNCTION_NAME=iantest02-rekognitionFunction-GWOFHB03EOHA
#     aws lambda invoke --function-name $FUNCTION_NAME --log-type Tail --payload '{"media": {"file": [{"s3bucket": "mybucket","s3key": "media/my_video.mp4"}]}}' outputfile.txt
#     cat outputfile.txt
#
###############################################################################

import json
import os
import urllib
import boto3
import sys

# TODO: figure out where to import mas_helper from
# from mas_helper import OutputHelper
# from mas_helper import MasExecutionError
#
# operator_name = 'transcribe'
# output_object = OutputHelper(operator_name)

def start_image_label_detection(bucket, key):
    rek = boto3.client('rekognition')
    response = rek.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':key}})
    print('Detected labels for ' + key)
    for label in response['Labels']:
        print (label['Name'] + ' : ' + str(label['Confidence']))
    return {"JobStatus": "SUCCEEDED"}

# Code for calling Rekognition Video operations
# Reference: https://docs.aws.amazon.com/code-samples/latest/catalog/python-rekognition-rekognition-video-python-stored-video.py.html
def start_video_label_detection(bucket, key):
    rek = boto3.client('rekognition')
    response = rek.start_label_detection(
        Video={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        },
        NotificationChannel={
            'SNSTopicArn': os.environ['REKOGNITION_SNS_TOPIC_ARN'],
            'RoleArn': os.environ['REKOGNITION_ROLE_ARN']
        })
    print('Start Job Id: ' + response['JobId'])
    return response['JobId']

# Lambda function entrypoint:
def lambda_handler(event, context):
    JobId=''
    response=''

    s3bucket = event["input"]["media"]["file"]["s3bucket"]
    s3key = event["input"]["media"]["file"]["s3key"]
    print("Processing s3://"+s3bucket+"/"+s3key)
    valid_video_types = [".avi", ".mp4", ".mov"]
    valid_image_types = [".png", ".jpg", ".jpeg"]
    file_type = os.path.splitext(s3key)[1]

    if file_type in valid_image_types:
        response = start_image_label_detection(s3bucket, urllib.parse.unquote_plus(s3key))
        return {"JobStatus": "SUCCEEDED"}
    elif file_type in valid_video_types:
        JobId = start_video_label_detection(s3bucket, urllib.parse.unquote_plus(s3key))
        return {"JobStatus": "IN_PROGRESS", "JobId": JobId}
    else:
        print("ERROR: invalid file type")
        #TODO: uncomment this after you figure out how to import mas_helper
        #     output_object.update_status("Error")
        #     output_object.update_metadata(transcribe_error="Not a valid file type")
        #     raise MasExecutionError(output_object.return_output_object())
    return {"JobStatus": "ERROR"}

