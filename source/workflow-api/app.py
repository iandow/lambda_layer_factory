from chalice import Chalice
from chalice import BadRequestError, ChaliceViewError
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
app = Chalice(app_name=APP_NAME)
app.debug = True

# Setup logging
logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)

WORKFLOW_TABLE_NAME = os.environ["WORKFLOW_TABLE_NAME"]
STAGE_TABLE_NAME = os.environ["STAGE_TABLE_NAME"]
WORKFLOW_EXECUTION_TABLE_NAME = os.environ["WORKFLOW_EXECUTION_TABLE_NAME"]
STAGE_EXECUTION_QUEUE_URL = os.environ["STAGE_EXECUTION_QUEUE_URL"]

# DynamoDB
DYNAMO_CLIENT = boto3.client("dynamodb")
DYNAMO_RESOURCE = boto3.resource("dynamodb")

# Step Functions
SFN_FUNCTION_CLIENT = boto3.client('stepfunctions')

# Simple Queue Service
SQS_RESOURCE = boto3.resource('sqs')
SQS_CLIENT = boto3.client('sqs')

# Environment

DEFAULT_WORKFLOW_SQS = {
    "name": "mas-Default",
    "StartAt": "Preprocess",
    "Stages": {
        "Preprocess": {
            "Type": "NestedQueue",
            "Resource": STAGE_EXECUTION_QUEUE_URL,
            "Next": "Analysis"
        },
        "Analysis": {
            "Type": "NestedQueue",
            "Resource": STAGE_EXECUTION_QUEUE_URL,
            "Next": "Postprocess"
        },
        "Postprocess": {
            "Type": "NestedQueue",
            "Resource": STAGE_EXECUTION_QUEUE_URL,
            "End": True
        }
    }
}


WORKFLOW_STATUS_STARTED = "Started"
WORKFLOW_STATUS_ERROR = "Error"
WORKFLOW_STATUS_COMPLETE = "Complete"

STAGE_STATUS_NOT_STARTED = "Not Started"
STAGE_STATUS_STARTED = "Started"
STAGE_STATUS_EXECUTING = "Executing"
STAGE_STATUS_ERROR = "Error"
STAGE_STATUS_COMPLETE = "Complete"

# Helper class to convert a DynamoDB item to JSON.


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


def results_pager(list_function, list_locator, attr_transform):
    results = []
    next_token = None
    try:
        while True:
            if next_token is None or len(next_token) == 0:
                service_response = list_function()
            else:
                service_response = list_function(NextToken=next_token)
            results = results + list_locator(service_response)
            # check the paging token
            if "NextToken" in service_response:
                next_token = service_response["NextToken"]
            else:
                break
            if len(next_token) == 0:
                break
        for item in results:
            item = attr_transform(item)
    except Exception as e:
        print(e)
    return results


@app.route('/')
def index():
    return {'hello': 'world'}


# Build a workflow orchestrated with queues
# In:
#    {
#    "name":"Default",
#    "stageConfiguration": {
#        {
#        Preprocess": {
#            Operations: {
#               "SplitAudio": {
#                   "enabled": True,
#                   "mediaTypes": {
#                       "video": True/False,
#                       "audio": True/False,
#                       "segment": True/False
#                       "frame": True/False
#                    }
#                },
#            },
#        }
#        ...
#        }
#     }
#
# Inputs override stage defaults
@app.route('/workflow', cors=True, methods=['POST'])
def create_workflow():

    table_name = WORKFLOW_TABLE_NAME

    try:
        table = DYNAMO_RESOURCE.Table(table_name)

        print(app.current_request.json_body)

        workflow_configuration = app.current_request.json_body

        # temporary scaffolding - support only 3 stage pipeline for MAS
        workflow = DEFAULT_WORKFLOW_SQS

        # save workflow configuration

        workflow = initialize_workflow_execution(
            workflow, workflow_configuration)

        print(json.dumps(workflow))
        #workflow["createTime"] = int(time.time())
        table.put_item(Item=workflow)

    except Exception as e:
        logger.info("Exception {}".format(e))
        workflow = None
        raise ChaliceViewError("Exception '%s'" % e)

    return workflow

# Build a stage
# In:
#    {
#    "name":"",
#    "mediaTypes: []"
#    "Operations: {
#        OperationName: {
#            "mediaType":mediaType,
#            "inputs": {
#                inputName: {
#                    "type": typeName,
#                ...}}
#     }
#     baseStateMachineArn:
#     stateMachineArn:
#     }
#
# Inputs override stage defaults


@app.route('/workflow/stage', cors=True, methods=['POST'])
def create_stage():

    table_name = STAGE_TABLE_NAME

    try:
        table = DYNAMO_RESOURCE.Table(table_name)

        print(app.current_request.json_body)

        stage = app.current_request.json_body

        # temporary scaffolding - support only 3 stage pipeline for MAS
        workflow = DEFAULT_WORKFLOW_SQS

        # save workflow configuration

        workflow = initialize_workflow_execution(
            workflow, workflow_configuration)

        #workflow["createTime"] = int(time.time())
        table.put_item(Item=workflow)

    except Exception as e:
        logger.info("Exception {}".format(e))
        workflow = None
        raise ChaliceViewError("Exception '%s'" % e)

    return workflow


def initialize_workflow_execution(workflow, workflow_configuration):

    for stage, configuration in workflow_configuration.items():

        # Override default configuration with passed in configuration
        if "stageConfiguration" in workflow_configuration:
            if stage in workflow["Stages"]:
                workflow["Stages"][stage]["Configuration"] = configuration
            else:
                workflow = None
                raise ChaliceViewError("Exception: Invalid stage '%s'" % stage)

    for stage in workflow["Stages"]:
        workflow["Stages"][stage]["status"] = STAGE_STATUS_NOT_STARTED
        workflow["Stages"][stage]["metrics"] = {}

    return workflow


@app.route('/workflow/{workflowId}')
def get_workflow_by_id():
    response = {}
    return response


@app.route('/workflow')
def get_workflow():
    response = {}
    return response


# In:
#     workflowId
#     mediaType
#     s3Object
#     parentWorkflowExecutionId
#
# create guid or compound key (video, segment, frame, version)
# Build a workflow orchestrated with queues
# In:
#    {
#    "name":"Default",
#    "input": {
#        "media": {
#            type:object
#         }
#         "metadata": {}
#    "stageConfiguration": {
#        {
#        Preprocess": {
#            Operations: {
#               "SplitAudio": {
#                   "enabled": True,
#                   "mediaTypes": {
#                       "video": True/False,
#                       "audio": True/False,
#                       "frame": True/False
#                    }
#                },
#            },
#        }
#        ...
#        }
#     }
#
# stageConfiguration Inputs override workflow stage defaults

@app.route('/workflow/execution', cors=True, methods=['POST'])
def create_workflow_execution_api():

    print(app.current_request.json_body)
    workflow_execution = app.current_request.json_body

    return create_workflow_execution("api", workflow_execution)


@app.lambda_function()
def create_workflow_execution_s3(event, context):

    print(event)

    workflow_execution = {
        "name": "mas-Default",
        "input": {
            "media": {
                "video": {
                    "s3bucket": "foo2",
                    "s3key": "bar"
                }
            }

        }
    }

    return create_workflow_execution("s3", workflow_execution)


def create_workflow_execution(trigger, workflow_execution):
    workflow_table_name = WORKFLOW_TABLE_NAME
    execution_table_name = WORKFLOW_EXECUTION_TABLE_NAME

    try:
        workflow_table = DYNAMO_RESOURCE.Table(workflow_table_name)
        execution_table = DYNAMO_RESOURCE.Table(execution_table_name)

        workflow_execution['id'] = str(uuid.uuid4())
        workflow_execution["trigger"] = trigger
        workflow_execution["current_stage"] = None

        workflow_execution["globals"] = {"media": {}, "metadata": {}}
        workflow_execution["globals"] = workflow_execution["input"]

        # lookup base workflow
        response = workflow_table.get_item(
            Key={
                'name': workflow_execution['name']
            })

        # lookup workflow defintiion we need to execute
        if "Item" in response:
            workflow = response["Item"]
        else:
            workflow_execution["workflow"] = None
            raise ChaliceViewError(
                "Exception: workflow id '%s' not found" % workflow_execution["workflowId"])

        workflow_execution["workflow"] = initialize_workflow_execution(
            workflow, workflow_execution)

        workflow_execution = start_first_stage_execution(
            "workflow", workflow_execution)

        print(json.dumps(workflow))
        execution_table.put_item(Item=workflow_execution)

    except Exception as e:
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception '%s'" % e)

    return workflow_execution


def start_first_stage_execution(trigger, workflow_execution):

    try:
        print("STARTING FIRST STAGE")

        print(workflow_execution)
        current_stage = workflow_execution["workflow"]["StartAt"]
        workflow_execution["current_stage"] = current_stage

        workflow_execution["workflow"]["Stages"][current_stage]["input"] = workflow_execution["globals"]
        #workflow_execution["workflow"]["Stages"][current_stage]["metrics"]["queue_time"] = int(
        #    time.time())
        workflow_execution["workflow"]["Stages"][current_stage]["status"] = STAGE_STATUS_STARTED

        try:
            logger.info("Starting next stage for workflow_execution_id:"+workflow_execution["id"])
            logger.info(json.dumps(
                workflow_execution["workflow"]["Stages"][current_stage]))

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

    except Exception as e:
        workflow_execution["status"] = WORKFLOW_STATUS_ERROR
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)
    return workflow_execution


def lambda_arn(name):

    REGION = os.environ["AWS_REGION"]
    ACCOUNT = os.environ["AWS_ACCOUNT"]

    arn = "arn:aws:lambda:"+REGION+":"+ACCOUNT + \
        ":function:"+APP_NAME+"-"+API_STAGE+"-"+name

    return arn

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

        print("GET STAGE AND EXECUTE STAGE STEP FUNCTION")
        print(stage)
        # FIXME code goes here

        print("REGISTER STEP FUNCTION ARN WITH CONTROL PLANE")
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

    arn = "arn:aws:lambda:"+REGION+":"+ACCOUNT + \
        ":function:"+APP_NAME+"-"+API_STAGE+"-"+name

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

        print(workflow_execution["workflow"]["Stages"]
              [workflow_execution["current_stage"]])

        workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]
                                                 ]["outputs"] = outputs

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
            #workflow_execution["workflow"]["Stages"][current_stage]["metrics"]["queue_time"] = int(
            #    time.time())
            workflow_execution["workflow"]["Stages"][current_stage]["status"] = STAGE_STATUS_STARTED

            try:
                logger.info("Starting next stage for workflow_execution_id {}:")
                logger.info(json.dumps(
                    workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]]))

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

# Build a workflow orchestrated with step functions
