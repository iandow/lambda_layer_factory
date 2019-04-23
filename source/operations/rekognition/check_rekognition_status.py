###############################################################################
# PURPOSE:
#   Lambda function to check Rekognition video labeling job status
#
# INPUT:
#   event.JobId = the job id to check status of.
#
# RETURNS:
#   IN_PROGRESS if job is still running
#   SUCCEEDED if job completed.
#
# REFERENCE:
# https://github.com/awsdocs/amazon-rekognition-developer-guide/blob/master/code_examples/python_examples/stored_video/python-rek-video.py
###############################################################################

import os
import boto3

def lambda_handler(event, context):
    print(event)
    # Images will have already been processed, so return if job status is already set.
    if event['JobStatus'] == "SUCCEEDED":
        return {"JobStatus": "SUCCEEDED"}
    JobId=event['JobId']
    rek = boto3.client('rekognition')
    maxResults = 1000
    paginationToken = ''
    finished = False
    # Pagination starts on 1001th result, so loop through each page.
    while finished == False:
        response = rek.get_label_detection(JobId=JobId,
                                           MaxResults=maxResults,
                                           NextToken=paginationToken,
                                           SortBy='TIMESTAMP')
        if response['JobStatus'] == "IN_PROGRESS":
            return {"JobStatus": "IN_PROGRESS", "JobId": JobId}

        elif response['JobStatus'] == "SUCCEEDED":

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

            return {"JobStatus": "SUCCEEDED"}

        return {"JobStatus": "ERROR"}


