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
import awsmas
# FIXME - why does importing awsmas not work?
WORKFLOW_STATUS_STARTED = "Started"
WORKFLOW_STATUS_ERROR = "Error"
WORKFLOW_STATUS_COMPLETE = "Complete"

STAGE_STATUS_NOT_STARTED = "Not Started"
STAGE_STATUS_STARTED = "Started"
STAGE_STATUS_EXECUTING = "Executing"
STAGE_STATUS_ERROR = "Error"
STAGE_STATUS_COMPLETE = "Complete"

OPERATION_STATUS_NOT_STARTED = "Not Started"
OPERATION_STATUS_STARTED = "Started"
OPERATION_STATUS_EXECUTING = "Executing"
OPERATION_STATUS_ERROR = "Error"
OPERATION_STATUS_COMPLETE = "Complete"

APP_NAME = "workflow-api"
API_STAGE = "dev"
#app = Chalice(app_name=APP_NAME)
#app.debug = True

# Setup logging
# Logging Configuration
#extra = {'requestid': app.current_request.context}
# fmt = '[%(levelname)s] [%(funcName)s] - %(message)s'
# logger = logging.getLogger('LUCIFER')
# logging.basicConfig(format=fmt)
# root = logging.getLogger()
# if root.handlers:
#     for handler in root.handlers:
#         root.removeHandler(handler)
# logging.basicConfig(format=fmt)
logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)


WORKFLOW_TABLE_NAME = os.environ["WORKFLOW_TABLE_NAME"]
STAGE_TABLE_NAME = os.environ["STAGE_TABLE_NAME"]
OPERATION_TABLE_NAME = os.environ["OPERATION_TABLE_NAME"]
WORKFLOW_EXECUTION_TABLE_NAME = os.environ["WORKFLOW_EXECUTION_TABLE_NAME"]
STAGE_EXECUTION_QUEUE_URL = os.environ["STAGE_EXECUTION_QUEUE_URL"]

# DynamoDB
DYNAMO_CLIENT = boto3.client("dynamodb")
DYNAMO_RESOURCE = boto3.resource("dynamodb")

# Step Functions
SFN_CLIENT = boto3.client('stepfunctions')

# Simple Queue Service
SQS_RESOURCE = boto3.resource('sqs')
SQS_CLIENT = boto3.client('sqs')

def complete_stage_execution_lambda(event, context):
    print(event)
    return complete_stage_execution("lambda", event["status"], event["outputs"], event["workflow_execution_id"])


def complete_stage_execution(trigger, status, outputs, workflow_execution_id):
    execution_table_name = WORKFLOW_EXECUTION_TABLE_NAME

    try:

        execution_table = DYNAMO_RESOURCE.Table(execution_table_name)
        # lookup the workflow
        response = execution_table.get_item(
            Key={
                'id': workflow_execution_id
            })
        #
        #  lookup workflow defintiion we need to execute
        if "Item" in response:
            workflow_execution = response["Item"]
        else:
            workflow_execution = None
            #raise ChaliceViewError(
            raise ValueError(
                "Exception: workflow execution id '%s' not found" % workflow_execution_id)

        stage = workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]]
        stage['name'] = workflow_execution["current_stage"]

        print("STAGE NAME")
        print(stage['name'])

        stage_outputs = outputs

        # Roll up operation status
        # # if any operation did not complete successfully, the stage has failed
        status = STAGE_STATUS_COMPLETE
        for operation in outputs:
            if operation["status"] != OPERATION_STATUS_COMPLETE:
                status = STAGE_STATUS_ERROR                

        workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]
                                                 ]["status"] = status

        print(workflow_execution["workflow"]["Stages"]
              [workflow_execution["current_stage"]])

        workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]
                                                 ]["outputs"] = stage_outputs

        print(json.dumps(stage_outputs))

        if "metadata" not in workflow_execution['globals']:
            workflow_execution['globals']["metadata"] = {}

        # Roll up operation media and metadata outputs
        for operation_outputs in outputs:
            if "media" in operation:
                for mediaType in operation_outputs["media"].keys():
                    # replace media with trasformed or created media from this stage
                    print(mediaType)
                    workflow_execution['globals']["media"][mediaType] = operation_outputs["media"][mediaType]
        
            if "metadata" in operation_outputs:
                for key in operation_outputs["metadata"].keys():
                    print(key)
                    workflow_execution['globals']["metadata"][key] = operation_outputs["metadata"][key]

        # Save the workflow status
        execution_table.put_item(Item=workflow_execution)
        
        if status == STAGE_STATUS_COMPLETE:
            workflow_execution = start_next_stage_execution(
                "workflow", workflow_execution)

        # Save the workflow status
        execution_table.put_item(Item=workflow_execution)

    except Exception as e:

        stage = None
        logger.info("Exception {}".format(e))
        #raise ChaliceViewError(
        raise ValueError(
            "Exception: '%s'" % e)

    return workflow_execution


def start_next_stage_execution(trigger, workflow_execution):

    try:
        print("START NEXT STAGE")

        print(workflow_execution)
        current_stage = workflow_execution["current_stage"]

        if "End" in workflow_execution["workflow"]["Stages"][current_stage] and workflow_execution["workflow"]["Stages"][current_stage]["End"] == True:

            workflow_execution["current_stage"] = "End"
            workflow_execution["status"] = WORKFLOW_STATUS_COMPLETE

        elif "Next" in workflow_execution["workflow"]["Stages"][current_stage]:
            current_stage = workflow_execution["current_stage"] = workflow_execution[
                "workflow"]["Stages"][current_stage]["Next"]

            workflow_execution["workflow"]["Stages"][current_stage]["input"] = workflow_execution["globals"]
            # workflow_execution["workflow"]["Stages"][current_stage]["metrics"]["queue_time"] = int(
            #    time.time())
            workflow_execution["workflow"]["Stages"][current_stage]["status"] = STAGE_STATUS_STARTED

            try:
                logger.info(
                    "Starting next stage for workflow_execution_id {}:")
                logger.info(json.dumps(
                    workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]]))

                workitem = {
                    "workflow_execution_id": workflow_execution["id"],
                    "workitem": {
                        "stageName": current_stage,
                        "stage": workflow_execution["workflow"]["Stages"][current_stage]
                    }
                }

                print("QUEUE workitem:")
                print(json.dumps(workitem))
                response = SQS_CLIENT.send_message(
                    QueueUrl=workflow_execution["workflow"]["Stages"][current_stage]["Resource"],
                    MessageBody=json.dumps(workitem)
                )
            except Exception as e:

                workflow_execution["status"] = WORKFLOW_STATUS_ERROR
                logger.info("Exception {}".format(e))
                #raise ChaliceViewError(
                raise ValueError(
                    "Exception: unable to queue work item '%s'" % e)

    except Exception as e:
        workflow_execution["status"] = WORKFLOW_STATUS_ERROR
        logger.info("Exception {}".format(e))
        #raise ChaliceViewError(
        raise ValueError(
            "Exception: '%s'" % e)
    return workflow_execution
