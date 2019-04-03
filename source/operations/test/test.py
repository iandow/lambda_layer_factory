import boto3
from boto3 import resource
from botocore.client import ClientError

import uuid
import logging
import os
#from datetime import date
#from datetime import time
from datetime import datetime
import json
import time
import decimal

logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)

def video_test_lambda(event, context):
    logger.info(event)

    video = {
        "s3bucket": "media-analysis-us-east-1-526662735483", 
        "s3key": "video_test_lamabda was here!"
    }

    output = {}
    output["name"] = "test-video-operation"
    output["media"] = {}
    output["media"]["video"] = video
    #output["metadata"] = event["input"]["metadata"]
    output["status"] = "Complete"
    output["message"] = "Everything is great!"

    event["output"] = {}
    event["output"]["test-video-operation"] = output

    return output


def audio_test_lambda(event, context):
    logger.info(event)

    audio = {
        "s3bucket": "media-analysis-us-east-1-526662735483", 
        "s3key": "audio_test_lamabda was here!"
    }
    
    output = {}
    output["name"] = "test-operation"
    output["media"] = {}
    output["media"]["audio"] = audio
    #output["metadata"] = event["input"]["metadata"]
    output["status"] = "Complete"
    output["message"] = "Everything is great!"

    event["output"] = {}
    event["output"]["test-audio-operation"] = output

    return output


def audio_test_duplicate_media_lambda(event, context):
    logger.info(event)

    audio = {
        "s3bucket": "media-analysis-us-east-1-526662735483", 
        "s3key": "audio_test_lamabda was here!"
    }
    
    output = {}
    output["name"] = "test-operation"
    output["media"] = {}
    output["media"]["audio"] = audio
    #output["metadata"] = event["input"]["metadata"]
    output["status"] = "Complete"
    output["message"] = "Everything is great!"

    event["output"] = {}
    event["output"]["test-audio-operation"] = output

    return output
