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

    output = {}
    output["name"] = "test-operation"
    output["media"] = event["input"]["media"]
    output["metadata"] = event["input"]["metadata"]
    output["status"] = "Complete"

    return output


