# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

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
    '''
    event is a stage execution object
    '''
    logger.info(json.dumps(event))
    return complete_stage_execution("lambda", event["status"], event["outputs"], event["workflow_execution_id"])


def complete_stage_execution(trigger, status, outputs, workflow_execution_id):

    try:

        execution_table = DYNAMO_RESOURCE.Table(WORKFLOW_EXECUTION_TABLE_NAME)
        # lookup the workflow
        response = execution_table.get_item(
            Key={
                'id': workflow_execution_id
            },
            ConsistentRead=True)

        if "Item" in response:
            workflow_execution = response["Item"]
        else:
            workflow_execution = None
            # raise ChaliceViewError(
            raise ValueError(
                "Exception: workflow execution id '%s' not found" % workflow_execution_id)

        logger.info("workflow_execution: {}".format(
            json.dumps(workflow_execution)))

        # Roll-up the results of the stage execution.  If anything fails here, we will fail the
        # stage, but still attempt to update the workflow execution the stage belongs to
        try:
            # Roll up operation status
            # # if any operation did not complete successfully, the stage has failed
            opstatus = awsmas.STAGE_STATUS_COMPLETE
            errorMessage = "none"
            for operation in outputs:
                if operation["status"] != awsmas.OPERATION_STATUS_COMPLETE:
                    opstatus = awsmas.STAGE_STATUS_ERROR
                    if "message" in operation:
                        errorMessage = "Stage failed because operation {} execution failed. Message: {}".format(
                            operation["name"], operation["message"])
                    else:
                        errorMessage = "Stage failed because operation {} execution failed.".format(
                            operation["name"])

            # don't overwrite an error
            if status != awsmas.STAGE_STATUS_ERROR:
                status = opstatus

            logger.info("Stage status: {}".format(status))

            workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]
                                                     ]["outputs"] = outputs

            if "metadata" not in workflow_execution['globals']:
                workflow_execution['globals']["metadata"] = {}

            # Roll up operation media and metadata outputs from this stage and add them to
            # the global workflow data:
            #
            #     1. mediaType and metatdata output keys must be unique withina stage - if
            #        non-unique keys are found across operations within a stage, then the
            #        stage execution will fail.
            #     2. if a stage has a duplicates a mediaType or metadata output key from the globals,
            #        then the global value is replaced by the stage output value

            # Roll up media
            stageOutputMediaTypeKeys = []
            for operation in outputs:
                if "media" in operation:
                    for mediaType in operation["media"].keys():
                        # replace media with trasformed or created media from this stage
                        print(mediaType)
                        if mediaType in stageOutputMediaTypeKeys:

                            raise ValueError(
                                "Duplicate mediaType '%s' found in operation ouput media.  mediaType keys must be unique within a stage." % mediaType)
                        else:
                            workflow_execution['globals']["media"][mediaType] = operation["media"][mediaType]
                            stageOutputMediaTypeKeys.append(mediaType)

                # Roll up metadata
                stageOutputMetadataKeys = []
                if "metadata" in operation:
                    for key in operation["metadata"].keys():
                        print(key)
                        if key in stageOutputMetadataKeys:
                            raise ValueError(
                                "Duplicate key '%s' found in operation ouput metadata.  Metadata keys must be unique within a stage." % key)
                        else:
                            workflow_execution['globals']["metadata"][key] = operation["metadata"][key]
                            stageOutputMetadataKeys.append(key)

            workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]
                                                     ]["status"] = status

        # The status roll up failed.  Handle the error and fall through to update the workflow status
        except Exception as e:

            logger.info("Exception while rolling up stage status {}".format(e))
            workflow_execution["message"] = "Exception while rolling up stage status {}".format(
                e)
            workflow_execution["status"] = awsmas.WORKFLOW_STATUS_ERROR
            status = awsmas.STAGE_STATUS_ERROR
            execution_table.put_item(Item=workflow_execution)
            raise ValueError("Error rolling up stage status: %s" % e)

        # Save the new stage and workflow status
        response = execution_table.update_item(
            Key={
                'id': workflow_execution_id
            },
            UpdateExpression='SET workflow.Stages.#stage = :stage, globals = :globals',
            ExpressionAttributeNames={
                '#stage': workflow_execution["current_stage"]
            },
            ExpressionAttributeValues={
                # ':stage': json.dumps(stage)
                ':stage': workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]],
                ':globals': workflow_execution["globals"]
                # ':step_function_arn': step_function_execution_arn
            }
        )

        # Start the next stage for execution
        if status == awsmas.STAGE_STATUS_COMPLETE:
            workflow_execution = start_next_stage_execution(
                "workflow", workflow_execution)

    except Exception as e:

        # FIXME - need a try/catch here? Try to save the status
        workflow_execution["status"] = awsmas.WORKFLOW_STATUS_ERROR
        execution_table.put_item(Item=workflow_execution)

        logger.info("Exception {}".format(e))

        raise ValueError(
            "Exception: '%s'" % e)

    return workflow_execution


def start_next_stage_execution(trigger, workflow_execution):

    try:
        print("START NEXT STAGE")

        execution_table = DYNAMO_RESOURCE.Table(WORKFLOW_EXECUTION_TABLE_NAME)

        current_stage = workflow_execution["current_stage"]
        workflow_execution["id"]

        if "End" in workflow_execution["workflow"]["Stages"][current_stage]:

            if workflow_execution["workflow"]["Stages"][current_stage]["End"] == True:
                workflow_execution["current_stage"] = "End"
                workflow_execution["status"] = awsmas.WORKFLOW_STATUS_COMPLETE

            # Save the new stage and workflow status
            response = execution_table.update_item(
                Key={
                    'id': workflow_execution["id"]
                },
                UpdateExpression='SET current_stage = :current_stage, #workflow_status = :workflow_status',
                ExpressionAttributeNames={
                    '#workflow_status': "status"
                },
                ExpressionAttributeValues={
                    ':current_stage': "End",
                    ':workflow_status': workflow_execution["status"]

                }
            )

        elif "Next" in workflow_execution["workflow"]["Stages"][current_stage]:
            current_stage = workflow_execution["current_stage"] = workflow_execution[
                "workflow"]["Stages"][current_stage]["Next"]

            workflow_execution["workflow"]["Stages"][current_stage]["input"] = workflow_execution["globals"]
            # workflow_execution["workflow"]["Stages"][current_stage]["metrics"]["queue_time"] = int(
            #    time.time())
            workflow_execution["workflow"]["Stages"][current_stage]["status"] = awsmas.STAGE_STATUS_STARTED

            try:
                logger.info(
                    "Starting next stage for workflow_execution_id {}:")
                logger.info(json.dumps(
                    workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]]))

                workitem = {
                    "workflow_execution_id": workflow_execution["id"],
                    "stage": workflow_execution["workflow"]["Stages"][current_stage]
                }

                # IMPORTANT: update the workflow_execution before queueing the work item...the
                # queued workitem must match the current stage when we start stage execution.
                # execution_table.put_item(Item=workflow_execution)
                response = execution_table.update_item(
                    Key={
                        'id': workflow_execution["id"]
                    },
                    UpdateExpression='SET workflow.Stages.#stage = :stage, current_stage = :current_stage, #workflow_status = :workflow_status',
                    ExpressionAttributeNames={
                        '#stage': workflow_execution["current_stage"],
                        '#workflow_status': "status"
                    },
                    ExpressionAttributeValues={
                        ':stage': workflow_execution["workflow"]["Stages"][current_stage],
                        ':current_stage': current_stage,
                        ':workflow_status': workflow_execution["status"]

                    }
                )

                print("QUEUE workitem:")
                print(json.dumps(workitem))
                response = SQS_CLIENT.send_message(
                    QueueUrl=workflow_execution["workflow"]["Stages"][current_stage]["Resource"],
                    MessageBody=json.dumps(workitem)
                )

            except Exception as e:

                workflow_execution["status"] = awsmas.WORKFLOW_STATUS_ERROR
                logger.info("Exception {}".format(e))

                # raise ChaliceViewError(
                raise ValueError(
                    "Exception: unable to queue work item '%s'" % e)

    except Exception as e:
        workflow_execution["status"] = awsmas.WORKFLOW_STATUS_ERROR
        logger.info("Exception {}".format(e))
        # raise ChaliceViewError(
        raise ValueError(
            "Exception: '%s'" % e)

    logger.info("workflow_execution: {}".format(
        json.dumps(workflow_execution)))
    return workflow_execution
