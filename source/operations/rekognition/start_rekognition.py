###############################################################################
# PURPOSE:
#   Lambda function to perform Rekognition tasks on image and video files
#
# SAMPLE INPUT:
#     {"media": {"file": [{"s3bucket": "ianwow","s3key": "my_image-gray.jpg"}]}}
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
    return response['Labels']

# Code for calling Rekognition Video operations
# Reference: https://docs.aws.amazon.com/code-samples/latest/catalog/python-rekognition-rekognition-video-python-stored-video.py.html
def start_video_label_detection(bucket, key):
    rek = boto3.client('rekognition')
    jobFound = False
    queueUrl=os.environ['REKOGNITION_SQS_QUEUE_URL']
    sqs = boto3.client('sqs')
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
    jobid=''
    response=''
    for record in event['media']['file']:
        s3bucket = record['s3bucket']
        s3key = record['s3key']
        print("Processing s3://"+s3bucket+"/"+s3key)
        valid_video_types = [".avi", ".mp4", ".mov"]
        valid_image_types = [".png", ".jpg", ".jpeg"]
        file_type = os.path.splitext(s3key)[1]

        if file_type in valid_image_types:
            response = start_image_label_detection(
                s3bucket,
                urllib.parse.unquote_plus(s3key)
            )
        elif file_type in valid_video_types:
            jobid = start_video_label_detection(
                s3bucket,
                urllib.parse.unquote_plus(s3key)
            )
        else:
            print("ERROR: invalid file type")
            #TODO: uncomment this after you figure out how to import mas_helper
            #     output_object.update_status("Error")
            #     output_object.update_metadata(transcribe_error="Not a valid file type")
            #     raise MasExecutionError(output_object.return_output_object())
    return {"response": response, "jobid": jobid}

