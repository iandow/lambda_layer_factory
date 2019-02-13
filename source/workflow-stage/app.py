from chalice import Chalice
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

APP_NAME = "workflow-api"
API_STAGE = "dev"

WORKFLOW_STATUS_STARTED = "Started"
WORKFLOW_STATUS_ERROR = "Error"
WORKFLOW_STATUS_COMPLETE = "Complete"

STAGE_STATUS_NOT_STARTED = "Not Started"
STAGE_STATUS_STARTED = "Started"
STAGE_STATUS_EXECUTING = "Executing"
STAGE_STATUS_ERROR = "Error"
STAGE_STATUS_COMPLETE = "Complete"


app = Chalice(app_name='workflow-stage')

WORKFLOW_TABLE_NAME = os.environ["WORKFLOW_TABLE_NAME"]
STAGE_TABLE_NAME = os.environ["STAGE_TABLE_NAME"]
WORKFLOW_EXECUTION_TABLE_NAME = os.environ["WORKFLOW_EXECUTION_TABLE_NAME"]
STAGE_EXECUTION_QUEUE_URL = os.environ["STAGE_EXECUTION_QUEUE_URL"]


@app.route('/')
def index():
    return {'hello': 'world'}

# @app.on_sqs_message(queue='Analysis', batch_size=1)
@app.lambda_function()
def test_execute_stage_lambda(event, context):
    stage = {"name": "foo"}
    step_function_execution_arn = "DUMMY:STEPFUNCTION:ARN"

    try:
        print("EVENT")
        print(json.dumps(event))

        for record in event["Records"]:
            message = json.loads(record["body"])
            print(message)

        workflow_execution_id = message["workflow_execution_id"]

        stage = get_stage_for_execution("workflow", workflow_execution_id)

        print("GET STAGE")
        print(stage)

        stage = start_stage_execution(
            "workflow", step_function_execution_arn, workflow_execution_id)

        print("START STAGE")
        print(stage)

        outputs = {
            "media": {
                "video": stage["name"],
                "audio": stage["name"]
            },
            "metadata": {
                "key1": stage["name"]
            }
        }

        stage = complete_stage_execution(
            "workflow", STAGE_STATUS_COMPLETE, outputs, workflow_execution_id)

        print("COMPLETE STAGE")
        print(stage)

    except Exception as e:
        print("eat the errors for now to avoid spin put on the queue")
        print(e)

    return stage

def lambda_arn(name):

    REGION = os.environ["AWS_REGION"]
    ACCOUNT = os.environ["AWS_ACCOUNT"]
    
    arn = "arn:aws:lambda:"+REGION+":"+ACCOUNT+":function:"+APP_NAME+"-"+API_STAGE+"-"+name
    
    return arn

@app.lambda_function()
def get_stage_for_execution_lambda(event, context):
    return get_stage_for_execution("lambda", event["workflow_execution_id"])

def get_stage_for_execution(trigger, workflow_execution_id):
    execution_table_name = WORKFLOW_EXECUTION_TABLE_NAME

    try:
        execution_table = DYNAMO_RESOURCE.Table(execution_table_name)
        # lookup the workflow
        response = execution_table.get_item(
            Key={
                'id': workflow_execution_id
            })
        # lookup workflow defintiion we need to execute
        if "Item" in response:
            workflow_execution = response["Item"]
        else:
            workflow_execution = None
            raise ChaliceViewError(
                "Exception: workflow execution id '%s' not found" % workflow_execution_id)

        stage = workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]]
        stage['name'] = workflow_execution["current_stage"]

    except Exception as e:

        stage = None
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)

    return stage

@app.lambda_function()
def start_stage_execution_lambda(event, context):
    return start_stage_execution("lambda", event["step_function_execution_arn"], event["workflow_execution_id"])

def start_stage_execution(trigger, step_function_execution_arn, workflow_execution_id):
    execution_table_name = WORKFLOW_EXECUTION_TABLE_NAME

    try:
        execution_table = DYNAMO_RESOURCE.Table(execution_table_name)
        # lookup the workflow
        response = execution_table.get_item(
            Key={
                'id': workflow_execution_id
            })
        # lookup workflow defintiion we need to execute
        if "Item" in response:
            workflow_execution = response["Item"]
        else:
            workflow_execution = None
            raise ChaliceViewError(
                "Exception: workflow execution id '%s' not found" % workflow_execution_id)

        stage = workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]]
        stage['name'] = workflow_execution["current_stage"]
        stage['status'] = STAGE_STATUS_EXECUTING
        stage['step_function_execution_arn'] = step_function_execution_arn

        workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]
                                                 ] = stage

        execution_table.put_item(Item=workflow_execution)

    except Exception as e:

        stage = None
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)

    return stage


@app.lambda_function()
def complete_stage_execution_lambda(event, context):
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
            raise ChaliceViewError(
                "Exception: workflow execution id '%s' not found" % workflow_execution_id)

        stage = workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]]
        stage['name'] = workflow_execution["current_stage"]

        print("STAGE NAME")
        print(stage['name'])

        workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]
                                                 ]["status"] = status
        
        print("CURRENT STAGE")
        print(stage['name'])

        print(workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]])

        workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]]["outputs"] = outputs
        
        print(json.dumps(outputs))

        # update workflow globals
        for mediaType in outputs["media"].keys():
            # replace media with trasformed or created media from this stage
            print(mediaType)
            workflow_execution['globals']["media"][mediaType] = outputs["media"][mediaType]
  
        if "metadata" not in workflow_execution['globals']:
            workflow_execution['globals']["metadata"] = {}

        for key in outputs["metadata"].keys():
            print(key)
            workflow_execution['globals']["metadata"][key] = outputs["metadata"][key]

        if status == STAGE_STATUS_COMPLETE:
            workflow_execution = start_next_stage_execution(
                "workflow", workflow_execution)

        # Save the workflow status
        execution_table.put_item(Item=workflow_execution)

    except Exception as e:

        stage = None
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)

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
            workflow_execution["workflow"]["Stages"][current_stage]["metrics"]["queue_time"] = int(
                    time.time())
            workflow_execution["workflow"]["Stages"][current_stage]["status"] = STAGE_STATUS_STARTED


        try:
            logger.info("Starting next stage for workflow_execution_id {}:")
            logger.info(json.dumps(workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]]))
            
            workitem = {
                "workflow_execution_id": workflow_execution["id"]
            }

            response = SQS_CLIENT.send_message(
                QueueUrl=workflow_execution["workflow"]["Stages"][current_stage]["Resource"],
                MessageBody=json.dumps(workitem)
            )
        except Exception as e:

            workflow_execution["status"] = WORKFLOW_STATUS_ERROR
            logger.info("Exception {}".format(e))
            raise ChaliceViewError(
                "Exception: unable to queue work item '%s'" % e)

    except Exception as e:
        workflow_execution["status"] = WORKFLOW_STATUS_ERROR
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)
    return workflow_execution

# The view function above will return {"hello": "world"}
# whenever you make an HTTP GET request to '/'.
#
# Here are a few more examples:
#
# @app.route('/hello/{name}')
# def hello_name(name):
#    # '/hello/james' -> {"hello": "james"}
#    return {'hello': name}
#
# @app.route('/users', methods=['POST'])
# def create_user():
#     # This is the JSON body the user sent in their POST request.
#     user_as_json = app.current_request.json_body
#     # We'll echo the json body back to the user in a 'user' key.
#     return {'user': user_as_json}
#
# See the README documentation for more examples.
#
