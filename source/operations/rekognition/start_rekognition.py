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

    # dotLine=0
    # while jobFound == False:
    #     sqsResponse = sqs.receive_message(QueueUrl=queueUrl, MessageAttributeNames=['ALL'], MaxNumberOfMessages=10)
    #     if sqsResponse:
    #         if 'Messages' not in sqsResponse:
    #             if dotLine<20:
    #                 print('.', end='')
    #                 dotLine=dotLine+1
    #             else:
    #                 print()
    #                 dotLine=0
    #             sys.stdout.flush()
    #             continue
    #
    #         for message in sqsResponse['Messages']:
    #             notification = json.loads(message['Body'])
    #             rekMessage = json.loads(notification['Message'])
    #             print(rekMessage['JobId'])
    #             print(rekMessage['Status'])
    #             if str(rekMessage['JobId']) == response['JobId']:
    #                 print('Matching Job Found:' + rekMessage['JobId'])
    #                 jobFound = True
    #                 #Change to match the start function earlier in this code.
    #                 #=============================================
    #                 GetResultsLabels(rekMessage['JobId'])
    #                 #self.GetResultsFaces(rekMessage['JobId'])
    #                 #self.GetResultsFaceSearchCollection(rekMessage['JobId'])
    #                 #self.GetResultsPersons(rekMessage['JobId'])
    #                 #self.GetResultsCelebrities(rekMessage['JobId'])
    #                 #self.GetResultsModerationLabels(rekMessage['JobId'])
    #
    #                 #=============================================
    #
    #                 sqs.delete_message(QueueUrl=queueUrl,
    #                                    ReceiptHandle=message['ReceiptHandle'])
    #             else:
    #                 print("Job didn't match:" +
    #                       str(rekMessage['JobId']) + ' : ' + str(response['JobId']))
    #             # Delete the unknown message. Consider sending to dead letter queue
    #             sqs.delete_message(QueueUrl=queueUrl,
    #                                ReceiptHandle=message['ReceiptHandle'])

    # print('done')

# Gets the results of labels detection by calling GetLabelDetection. Label
# detection is started by a call to StartLabelDetection.
# jobId is the identifier returned from StartLabelDetection
def GetResultsLabels(self, jobId):
    maxResults = 10
    paginationToken = ''
    finished = False

    while finished == False:
        response = self.rek.get_label_detection(JobId=jobId,
                                                MaxResults=maxResults,
                                                NextToken=paginationToken,
                                                SortBy='TIMESTAMP')

        print(response['VideoMetadata']['Codec'])
        print(str(response['VideoMetadata']['DurationMillis']))
        print(response['VideoMetadata']['Format'])
        print(response['VideoMetadata']['FrameRate'])

        for labelDetection in response['Labels']:
            label=labelDetection['Label']

            print("Timestamp: " + str(labelDetection['Timestamp']))
            print("   Label: " + label['Name'])
            print("   Confidence: " +  str(label['Confidence']))
            print("   Instances:")
            for instance in label['Instances']:
                print ("      Confidence: " + str(instance['Confidence']))
                print ("      Bounding box")
                print ("        Top: " + str(instance['BoundingBox']['Top']))
                print ("        Left: " + str(instance['BoundingBox']['Left']))
                print ("        Width: " +  str(instance['BoundingBox']['Width']))
                print ("        Height: " +  str(instance['BoundingBox']['Height']))
                print()
            print()
            print ("   Parents:")
            for parent in label['Parents']:
                print ("      " + parent['Name'])
            print ()

            if 'NextToken' in response:
                paginationToken = response['NextToken']
            else:
                finished = True

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

