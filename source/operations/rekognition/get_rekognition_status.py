import os
import boto3
import urllib3
import json

region = os.environ['AWS_REGION']
transcribe = boto3.client("rekognition")

def lambda_handler(event, context):
    print(event)


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


    return {"status": "Complete"}

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

