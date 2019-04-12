# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from chalice import Chalice
from chalice import NotFoundError, BadRequestError, ChaliceViewError, Response, ConflictError
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
import signal
#from urllib2 import build_opener, HTTPHandler, Request
from urllib.request import build_opener, HTTPHandler, Request
from chalicelib import awsmas

APP_NAME = "workflow-api"
API_STAGE = "dev"
app = Chalice(app_name=APP_NAME)
app.debug = True

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
STAGE_EXECUTION_ROLE = os.environ["STAGE_EXECUTION_ROLE"]
COMPLETE_STAGE_LAMBDA_ARN = os.environ["COMPLETE_STAGE_LAMBDA_ARN"]

# DynamoDB
DYNAMO_CLIENT = boto3.client("dynamodb")
DYNAMO_RESOURCE = boto3.resource("dynamodb")

# Step Functions
SFN_CLIENT = boto3.client('stepfunctions')

# Simple Queue Service
SQS_RESOURCE = boto3.resource('sqs')
SQS_CLIENT = boto3.client('sqs')

# IAM resource
IAM_CLIENT = boto3.client('iam')
IAM_RESOURCE = boto3.resource('iam')

# Helper class to convert a DynamoDB item to JSON.


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def checkRequiredInput(key, dict, objectname):
    
    if key not in dict:
        raise BadRequestError("Key '%s' is required in '%s' input" % (
            key, objectname))

@app.route('/')
def index():
    return {'hello': 'world'}

##############################################################################
#    ___                       _
#   / _ \ _ __   ___ _ __ __ _| |_ ___  _ __ ___
#  | | | | '_ \ / _ \ '__/ _` | __/ _ \| '__/ __|
#  | |_| | |_) |  __/ | | (_| | || (_) | |  \__ \
#   \___/| .__/ \___|_|  \__,_|\__\___/|_|  |___/
#        |_|
#
##############################################################################


@app.route('/workflow/operation', cors=True, methods=['POST'])
def create_operation_api():
    """ Registers a new operator with the workflow engine

    The body defines the configuration parameters for the operator, the 
    expected inputs and their data types as well as a state machine that 
    defines the operator.  The state machine must contain logic to make a 
    runtime decision of whether or not the opetator will execute based on the 
    inputs and configuration presented to it.  For example, if the input is an 
    audio file, the operator must check the configuration and decide if it can 
    process audio.  

    If a stateMachineArn is provided on the input, then the ASL for the 
    operator is copied from the exsting state machine.   Otherwise, the ASL 
    for the state machine must be specified in the body.

    Body: 
        {
            "name": "string",
            "configuration" : {
                "mediaType": "video",
                "enabled:": True,
                "configuration1": "value1",
                "configuration2": "value2",
                ...
            }
            "stateMachineArn":arn,
            "stateMachineExecutionRoleArn":arn

        }

    Returns:
        A dict mapping keys to the corresponding operation created including 
        the ASL for the duplicated state machine an id and a create time.

    Raises:
        200: The operation was created successfully.
        400: Bad Request - the input state machine ARN was not found or the 
             state machine ASL is invalid
        409: Conflict - an operation with the same name already exists
        500: Internal server error 
    """

    
    operation = app.current_request.json_body
    logger.info(operation)

    create_operation(operation)


def create_operation(operation):
        
    table_name = OPERATION_TABLE_NAME

    try:
        print("create_operation()")
        table = DYNAMO_RESOURCE.Table(table_name)
        logger.info(operation)

        # save operation configuration

        logger.info(json.dumps(operation))
        for k, v in operation.items():
            logger.info("{} {}".format(k, v))

        name = k

        checkRequiredInput("configuration", operation[name], "Operation Definition")
        checkRequiredInput("stateMachineArn", operation[name], "Operation Definition")
        #checkRequiredInput("stateMachineExecutionRoleArn", operation[name], "Operation Definition")
        checkRequiredInput("mediaType", operation[name]["configuration"], "Operation Definition Configuartion")
        checkRequiredInput("enabled", operation[name]["configuration"], "Operation Configuration")

        logger.info("Inputs are OK")

        operation["name"] = name
        operation['id'] = str(uuid.uuid4())
        operation['createTime'] = int(time.time())

        # FIXME get rid of opertion name as key in this
        if "stateMachineArn" in operation[name]:
            logger.info("lookup state machine for operation")
            response = SFN_CLIENT.describe_state_machine(
                stateMachineArn=operation[name]["stateMachineArn"]
            )

            operation["stateMachineASL"] = response["definition"]
            logger.info(response)
        elif "stateMachineAsl" in operation[name]:
            logger.info("Got ASL for operation")

        table.put_item(
            Item=operation, 
            ConditionExpression="attribute_not_exists(#operation_name)",
            ExpressionAttributeNames={
                    '#operation_name': "name"
                })

    except ClientError as e:
        # Ignore the ConditionalCheckFailedException, bubble up
        # other exceptions.
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            raise ConflictError("Operation with name {} already exists".format(name))
        else:
            raise
        
    except SFN_CLIENT.exceptions.NotFoundException as e:
        logger.error("SFN_CLIENT.exceptions.NotFoundException")
        raise BadRequestError("State machine ARN {} not found. Error: {}"
                            .format(operation[name]["stateMachineArn"], e))

    except Exception as e:
        logger.error("Exception {}".format(e))
        operation = None
        raise ChaliceViewError("Exception '%s'" % e)

    return operation


@app.route('/workflow/operation', cors=True, methods=['PUT'])
def update_operation():
    """ Update n operation NOT IMPLEMENTED 

    XXX

    """
    operation = {"Message": "Update on stages in not implemented"}
    return operation


@app.route('/workflow/operation', cors=True, methods=['GET'])
def list_operations():
    """ List all operation defintions

    Returns:
        A list of operation definitions.

    Raises:
        200: All operations returned sucessfully.
        500: Internal server error 
    """

    table = DYNAMO_RESOURCE.Table(OPERATION_TABLE_NAME)

    response = table.scan()
    operations = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        operations.extend(response['Items'])

    return operations


@app.route('/workflow/operation/{name}', cors=True, methods=['GET'])
def get_operation_by_name(name):
    """ Get an operation definition by name

    Returns:
        A dictionary contianing the operation definition.

    Raises:
        200: All operations returned sucessfully.
        404: Not found
        500: Internal server error 
    """
    operation_table = DYNAMO_RESOURCE.Table(OPERATION_TABLE_NAME)
    operation = None
    response = operation_table.get_item(
        Key={
            'name': name
        })

    if "Item" in response:
        operation = response["Item"]
    else:
        raise NotFoundError(
            "Exception: operation '%s' not found" % name)

    return operation

@app.route('/workflow/operation/{name}', cors=True, methods=['DELETE'])
def delete_operation(name):
    """ Delete a an operation

    Returns:  

    Raises:
        200: Operation deleted sucessfully.
        404: Not found
        500: Internal server error 
    """
    table = DYNAMO_RESOURCE.Table(OPERATION_TABLE_NAME)
    operation = {}

    try: 
        
        operation = {}
        response = table.get_item(
            Key={
                'name': name
            },
            ConsistentRead=True)
        
        if "Item" in response:
            operation = response["Item"]

            response = table.delete_item(
            Key={
                'name': name
            }) 

        else:
            
            operation["message"] = "Warning: operation '{}' not found".format(name)
            #raise NotFoundError(
            #    "Exception: operation '%s' not found" % name) 
    
    except Exception as e:

        operation = None
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)
    
    return operation


################################################################################################
#   ____  _
#  / ___|| |_ __ _  __ _  ___ ___
#  \___ \| __/ _` |/ _` |/ _ / __|
#   ___) | || (_| | (_| |  __\__ \
#  |____/ \__\__,_|\__, |\___|___/
#                  |___/
#
################################################################################################

@app.route('/workflow/stage', cors=True, methods=['POST'])
def create_stage_api():
    """ Create a stage state machine from a list of existing operations.  
    
    A stage is a set of operations that are grouped so they can be executed in parallel.
    When the stage is executed as part of a workflow, operations within a stage are executed as
    branches in a parallel state.  The generated state machines status is tracked by the 
    workflow engine control plane during execution.

    Body: 
        {
        "name":"stage-name",
        "operations": ["operation-name1", "operation-name2", ...]
        }

    Returns:
        A dict mapping keys to the corresponding stage created including 
        the ARN of the state machine created. 

        {
            "name": "stage-name",
            "operations": [
                "operation-name1",
                "operation-name2", 
                ...
            ],
            "configuration": {
                "operation-name1": operation-configuration-object1,
                "operation-name2": operation-configuration-object1,
                ...
            }
            "stateMachineArn": ARN-string
        }

    Raises:
        200: The stage was created successfully.
        400: Bad Request - one of the input state machines was not found or was invalid
        409: Conflict
        500: Internal server error 
    """
    
    stage = None
    
    stage = app.current_request.json_body

    logger.info(app.current_request.json_body)

    stage = create_stage(stage)

    return stage


def create_stage(stage):

    try:
        stage_table = DYNAMO_RESOURCE.Table(STAGE_TABLE_NAME)
        configuration = {}

        logger.info(stage)

        checkRequiredInput("name", stage, "Stage Definition")
        checkRequiredInput("operations", stage, "Stage Definition")

        name = stage["name"]
        stage["Resource"] = STAGE_EXECUTION_QUEUE_URL

        # Check if this stage already exists
        response = stage_table.get_item(
            Key={
                'name': name
            },
            ConsistentRead=True)
        
        if "Item" in response:
            raise ConflictError(
                "A stage with the name '%s' already exists" % name)

        # Build the stage state machine.  The stage machine consists of a parallel state with 
        # branches for each operator and a call to the stage completion lambda at the end.  
        # The parallel state takes a stage object as input.  Each
        # operator returns and operatorOutput object. The outputs for each operator are 
        # returned from the parallel state as elements of the "outputs" array.    
        stageAsl = {
            "StartAt": "Preprocess Media",
            "States": {
                "Complete Stage": {
                    "Type": "Task",
                    "Resource": COMPLETE_STAGE_LAMBDA_ARN,
                    "End": True
                }
            }
        }
        stageAsl["StartAt"] = name
        stageAsl["States"][name] = {
            "Type": "Parallel",
            "Next": "Complete Stage",
            "ResultPath": "$.outputs",
            "Branches": [
            ]
        }

        # Add a branch to the stage state machine for each operation, build up default 
        # configuration for the stage based on the operator configuration
        
        
        for op in stage["operations"]:
            # lookup base workflow
            operation = get_operation_by_name(op)
            #logger.info(json.dumps(operation))

            stageAsl["States"][name]["Branches"].append(
                json.loads(operation["stateMachineASL"]))
            
            configuration[op] = operation[op]["configuration"]

            #FIXME - construct Role to execute state machine from operation roles

            stageStateMachineExecutionRoleArn = operation[op]["stateMachineExecutionRoleArn"]

        logger.info(json.dumps(stageAsl))
        
        stage["configuration"] = configuration

        # Build stage
        response = SFN_CLIENT.create_state_machine(
            name=name,
            definition=json.dumps(stageAsl),
            roleArn=stageStateMachineExecutionRoleArn
        )    

        stage["stateMachineArn"] = response["stateMachineArn"]
        

        stage_table.put_item(Item=stage)

    except Exception as e:
        logger.info("Exception {}".format(e))
        stage = None
        raise ChaliceViewError("Exception '%s'" % e)

    return stage


@app.route('/workflow/stage', cors=True, methods=['PUT'])
def update_stage():
    """ Update a stage NOT IMPLEMENTED 

    XXX

    """
    stage = {"message":"NOT IMPLEMENTED"}
    return stage


@app.route('/workflow/stage', cors=True, methods=['GET'])
def list_stages():
    """ List all stage defintions

    Returns:
        A list of operation definitions.

    Raises:
        200: All operations returned sucessfully.
        500: Internal server error 
    """

    table = DYNAMO_RESOURCE.Table(STAGE_TABLE_NAME)

    response = table.scan()
    stages = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        stages.extend(response['Items'])

    return stages


@app.route('/workflow/stage/{name}', cors=True, methods=['GET'])
def get_stage_by_name(name):
    """ Get a stage definition by name

    Returns:
        A dictionary contianing the stage definition.

    Raises:
        200: All stages returned sucessfully.
        404: Not found
        500: Internal server error 
    """
    stage_table = DYNAMO_RESOURCE.Table(STAGE_TABLE_NAME)
    stage = None
    response = stage_table.get_item(
        Key={
            'name': name
        })

    if "Item" in response:
        stage = response["Item"]
    else:
        raise NotFoundError(
            "Exception: stage '%s' not found" % name)

    return stage

@app.route('/workflow/stage/{name}', cors=True, methods=['DELETE'])
def delete_stage(name):
    """ Delete a stage

    Returns:  

    Raises:
        200: Stage deleted sucessfully.
        404: Not found
        500: Internal server error 
    """
    table = DYNAMO_RESOURCE.Table(STAGE_TABLE_NAME)

    try: 
        
        stage = {}
        response = table.get_item(
            Key={
                'name': name
            },
            ConsistentRead=True)
        
        if "Item" in response:
            stage = response["Item"]

            # Delete the stage state machine 
            response = SFN_CLIENT.delete_state_machine(
                stateMachineArn=stage["stateMachineArn"]
            )

            response = table.delete_item(
                Key={
                    'name': name
                })
        else:
            stage["message"] = "Warning: stage '{}' not found".format(name)
        
    except Exception as e:

        stage = None
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)
    
    return stage

###############################################################################
#  __        __         _     __ _
#  \ \      / /__  _ __| | __/ _| | _____      _____
#   \ \ /\ / / _ \| '__| |/ / |_| |/ _ \ \ /\ / / __|
#    \ V  V / (_) | |  |   <|  _| | (_) \ V  V /\__ \
#     \_/\_/ \___/|_|  |_|\_\_| |_|\___/ \_/\_/ |___/
#
###############################################################################


@app.route('/workflow', cors=True, methods=['POST'])
def create_workflow_api():
    """ Create a workflow from a list of existing stages.  
    
    A workflow is a pipeline of stages that are executed sequentially to transform and 
    extract metadata for a set of mediaType objects.  Each stage must contain either a 
    "Next" key indicating the next stage to execute or and "End" key indicating it
    is the last stage.

    Body: 
        {
            "name": string,
            "StartAt": string - name of starting stage,
            "Stages": {
                "stage-name": {
                    "Next": "string - name of next stage"
                },
                ...,
                "stage-name": {
                    "End": true
                }
            }
        }
    

    Returns:
        A dict mapping keys to the corresponding workflow created including the 
        AWS resources used to execute each stage.        

        {
            "name": string,
            "StartAt": string - name of starting stage,
            "Stages": {
                "stage-name": {
                    "Resource": queueARN,
                    "StateMachine": stateMachineARN,
                    "configuration": stageConfigurationObject,
                    "Next": "string - name of next stage"
                },
                ...,
                "stage-name": {
                    "Resource": queueARN,
                    "StateMachine": stateMachineARN,
                    "configuration": stageConfigurationObject,
                    "End": true
                }
            }
        }
        

    Raises:
        200: The workflow was created successfully.
        400: Bad Request - one of the input stages was not found or was invalid
        500: Internal server error 
    """

    workflow = app.current_request.json_body
    logger.info(json.dumps(workflow))

    return create_workflow("api", workflow)


def create_workflow(trigger, workflow):
    try:
        workflow_table = DYNAMO_RESOURCE.Table(WORKFLOW_TABLE_NAME)

        workflow["trigger"] = trigger

        logger.info(json.dumps(workflow))

        
        #workflow["createTime"] = int(time.time())

        # Validate inputs

        checkRequiredInput("name", workflow, "Workflow Definition")
        checkRequiredInput("StartAt", workflow, "Workflow Definition")
        checkRequiredInput("Stages", workflow, "Workflow Definition")

        endcount = 0
        for name,stage in workflow["Stages"].items():

            # Stage must have an End or a Next key
            if "End" in stage and stage["End"] == True:
                endcount += 1
            elif "Next" in stage:  
                pass
            else:
                raise BadRequestError("Stage %s must have either an 'End' or and 'Next' key" % (
                    name))

        if endcount != 1:
            raise BadRequestError("Workflow %s must have exactly 1 'End' key within its stages" % (
                    workflow["name"]))
        

        for name, stage in workflow["Stages"].items():
            s = get_stage_by_name(name)
            stage.update(s)

        
        workflow_table.put_item(
            Item=workflow, 
            ConditionExpression="attribute_not_exists(#workflow_name)",
            ExpressionAttributeNames={
                    '#workflow_name': "name"
                })

    except ClientError as e:
        # Ignore the ConditionalCheckFailedException, bubble up
        # other exceptions.
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            raise ConflictError("Workflow with name {} already exists".format(name))
        else:
            raise
    
    except Exception as e:
        logger.info("Exception {}".format(e))
        workflow = None
        raise ChaliceViewError("Exception '%s'" % e)

    return workflow


@app.route('/workflow', cors=True, methods=['PUT'])
def update_workflow():
    """ Update a workflow NOT IMPLEMENTED 

    XXX

    """
    stage = {"message":"UPDATE WORKFLOW NOT IMPLEMENTED"}
    return stage


@app.route('/workflow', cors=True, methods=['GET'])
def list_workflows():
    """ List all workflow defintions

    Returns:
        A list of workflow definitions.

    Raises:
        200: All workflows returned sucessfully.
        500: Internal server error 
    """

    table = DYNAMO_RESOURCE.Table(WORKFLOW_TABLE_NAME)

    response = table.scan()
    workflows = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        workflows.extend(response['Items'])

    return workflows


@app.route('/workflow/{name}', cors=True, methods=['GET'])
def get_workflow_by_name(name):
    """ Get a workflow definition by name

    Returns:
        A dictionary contianing the workflow definition.

    Raises:
        200: All workflows returned sucessfully.
        404: Not found
        500: Internal server error 
    """
    table = DYNAMO_RESOURCE.Table(WORKFLOW_TABLE_NAME)
    workflow = None
    response = table.get_item(
        Key={
            'name': name
        })

    if "Item" in response:
        workflow = response["Item"]
    else:
        raise NotFoundError(
            "Exception: workflow '%s' not found" % name)

    return workflow

@app.route('/workflow/configuration/{name}', cors=True, methods=['GET'])
def get_workflow_configuration_by_name(name):
    """ Get a workflow configruation object by name

    Returns:
        A dictionary contianing the workflow configuration.

    Raises:
        200: All workflows returned sucessfully.
        404: Not found
        500: Internal server error 
    """
    table = DYNAMO_RESOURCE.Table(WORKFLOW_TABLE_NAME)
    workflow = None
    response = table.get_item(
        Key={
            'name': name
        })

    if "Item" in response:
        workflow = response["Item"]
        configuration = {}
        for name, stage in workflow["Stages"].items():
            configuration[name] = stage["configuration"]

    else:
        raise NotFoundError(
            "Exception: workflow '%s' not found" % name)

    return configuration

@app.route('/workflow/{name}', cors=True, methods=['DELETE'])
def delete_workflow(name):
    """ Delete a workflow

    Returns:  

    Raises:
        200: Workflow deleted sucessfully.
        404: Not found
        500: Internal server error 
    """
    table = DYNAMO_RESOURCE.Table(WORKFLOW_TABLE_NAME)

    try: 
        
        workflow = {}
        response = table.get_item(
            Key={
                'name': name
            },
            ConsistentRead=True)
        
        if "Item" in response:
            workflow = response["Item"]
            response = table.delete_item(
                Key={
                    'name': name
                })   
        else:
            workflow["Message"] = "Workflow '%s' not found" % name
        
    except Exception as e:

        workflow = None
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)
    
    return workflow


# ================================================================================================
#  __        __         _     __ _                 _____                     _   _
#  \ \      / /__  _ __| | __/ _| | _____      __ | ____|_  _____  ___ _   _| |_(_) ___  _ __  ___
#   \ \ /\ / / _ \| '__| |/ / |_| |/ _ \ \ /\ / / |  _| \ \/ / _ \/ __| | | | __| |/ _ \| '_ \/ __|
#    \ V  V / (_) | |  |   <|  _| | (_) \ V  V /  | |___ >  <  __/ (__| |_| | |_| | (_) | | | \__ \
#     \_/\_/ \___/|_|  |_|\_\_| |_|\___/ \_/\_/   |_____/_/\_\___|\___|\__,_|\__|_|\___/|_| |_|___/
#
# ================================================================================================

@app.route('/workflow/execution', cors=True, methods=['POST'])
def create_workflow_execution_api():
    """ Execute a workflow.  
    
    The Body contains the name of the workflow to execute, at least one input 
    media type within the media object.  A dictionary of stage configuration 
    objects can be passed in to override the default configuration of the operations
    within the stages.

    Body: 
        {
        "name":"Default",
        "input": media-object
        "configuration": {
            {
            "stage-name": {
                "operations: {
                    "SplitAudio": {
                       "enabled": True,
                       "mediaTypes": {
                           "video": True/False,
                           "audio": True/False,
                           "frame": True/False
                       }
                   },
               },
           }
           ...
           }
        }
    

    Returns:
        A dict mapping keys to the corresponding workflow execution created including 
        the workflowExecutionId, the AWS queue and state machine resources assiciated with
        the workflow execution and the current execution status of the workflow. 

        {
            "name": string,
            "StartAt": "Preprocess",
            "Stages": {
                "stage-name": {
                    "Type": "NestedQueue",
                    "Resource": queueARN,
                    "StateMachine": stateMachineARN,
                    "Next": "Analysis"
                },
                ...,
                "stage-name: {
                    "Type": "NestedQueue",
                    "Resource": queueARN,
                    "StateMachine": stateMachineARN,
                    "End": true
                }
            }
        }

    Raises:
        200: The workflow execution was created successfully.
        400: Bad Request - the input workflow was not found or was invalid
        500: Internal server error  
    """

    logger.info(app.current_request.json_body)
    workflow_execution = app.current_request.json_body

    return create_workflow_execution("api", workflow_execution)


@app.lambda_function()
def create_workflow_execution_s3(event, context):

    logger.info(event)

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

    execution_table = DYNAMO_RESOURCE.Table(WORKFLOW_EXECUTION_TABLE_NAME)

    try:
        
        name = workflow_execution["name"]
        input = workflow_execution["input"]
        configuration = workflow_execution["configuration"] if "configuration" in workflow_execution  else {}
        
        # BRANDON - make an asset
        
        workflow_execution = initialize_workflow_execution(trigger, name, input, configuration)

        execution_table.put_item(Item=workflow_execution)

        workflow_execution = start_first_stage_execution("workflow", workflow_execution)        


    except Exception as e:
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception '%s'" % e)

    return workflow_execution

def initialize_workflow_execution(trigger, name, input, configuration):
    
    workflow_table = DYNAMO_RESOURCE.Table(WORKFLOW_TABLE_NAME)

    workflow_execution = {}
    workflow_execution["id"] = str(uuid.uuid4())
    workflow_execution["trigger"] = trigger
    workflow_execution["current_stage"] = None
    workflow_execution["globals"] = {"media": {}, "metadata": {}}
    workflow_execution["globals"].update(input)  
    workflow_execution["configuration"] = configuration

    # lookup base workflow
    response = workflow_table.get_item(
        Key={
            'name': name
        },
        ConsistentRead=True)

    if "Item" in response:
        workflow = response["Item"]
    else:
        raise ChaliceViewError(
            "Exception: workflow id '%s' not found" % workflow_execution["workflowId"])

    # Initialize workflow stages for execution
    for stage, config in configuration.items():
        if stage in workflow["Stages"]:
            workflow["Stages"][stage]["Configuration"] = config
            
        else:
            workflow_execution["workflow"] = None
            raise ChaliceViewError("Exception: Invalid stage '%s'" % stage)

    for stage in workflow["Stages"]:
        workflow["Stages"][stage]["status"] = awsmas.STAGE_STATUS_NOT_STARTED
        workflow["Stages"][stage]["metrics"] = {}
        workflow["Stages"][stage]["name"] = stage
        workflow["Stages"][stage]["workflow_execution_id"] = workflow_execution["id"]
        # BRANDON - add the asset id here
        if "metadata" not in workflow["Stages"][stage]:
            workflow["Stages"][stage]["metadata"] = {}

    workflow_execution["workflow"] = workflow
    
    # initialize top level workflow_execution state from the workflow
    workflow_execution["status"] = awsmas.WORKFLOW_STATUS_STARTED
    workflow_execution["current_stage"] = current_stage = workflow["StartAt"]

    # setup the current stage for execution
    workflow_execution["workflow"]["Stages"][current_stage]["input"] = workflow_execution["globals"]
    # workflow_execution["workflow"]["Stages"][current_stage]["metrics"]["queue_time"] = int(
    #    time.time())
    workflow_execution["workflow"]["Stages"][current_stage]["status"] = awsmas.STAGE_STATUS_STARTED

    return workflow_execution

def start_first_stage_execution(trigger, workflow_execution):

    current_stage = workflow_execution["current_stage"] 

    try:
        logger.info(
            "Starting next stage for workflow_execution_id:"+workflow_execution["id"])
        logger.info(json.dumps(
            workflow_execution["workflow"]["Stages"][current_stage]))

        workitem = {
            "workflow_execution_id": workflow_execution["id"],
            "stage": workflow_execution["workflow"]["Stages"][current_stage]
        }

        logger.info("QUEUE workitem:")
        logger.info(json.dumps(workitem))

        response = SQS_CLIENT.send_message(
            QueueUrl=workflow_execution["workflow"]["Stages"][current_stage]["Resource"],
            MessageBody=json.dumps(workitem)
        )

    except Exception as e:
        workflow_execution["status"] = awsmas.WORKFLOW_STATUS_ERROR
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)
    
    return workflow_execution

# @app.on_sqs_message(queue='Analysis', batch_size=1)

@app.route('/workflow/execution/nextstage', cors=True, methods=['POST'])
def execute_next_stage():

    stage = app.current_request.json_body
    logger.info(stage)
    stage = execute_stage(stage)

    return stage


@app.lambda_function()
def execute_stage_lambda(event, context):

    try:
        logger.info("EVENT")
        logger.info(json.dumps(event))

        for record in event["Records"]:
            message = json.loads(record["body"])
            logger.info(message)

        stage = execute_stage(message)

    except Exception as e:
        # stage = complete_stage_execution(
        #        "workflow", STAGE_STATUS_ERROR, outputs, workflow_execution_id)
        #stage["exception"] = str(e)
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)

    return stage


def execute_stage(input_stage):

    try:
        workflow_execution_id = input_stage["workflow_execution_id"]

        stage = input_stage["stage"]
        stage["workflow_execution_id"] = workflow_execution_id

        logger.info(stage)
        response = SFN_CLIENT.start_execution(
            stateMachineArn=stage["stateMachineArn"],
            name=stage["name"]+workflow_execution_id,
            input=json.dumps(stage)
        )

        stage["stepFunctionExecutionArn"] = response['executionArn']

        logger.info("REGISTER STEP FUNCTION ARN WITH CONTROL PLANE")
        stage = start_stage_execution(
            "workflow", stage["stepFunctionExecutionArn"], workflow_execution_id)

    except Exception as e:
        # stage = complete_stage_execution(
        #        "workflow", STAGE_STATUS_ERROR, outputs, workflow_execution_id)
        #stage["exception"] = str(e)
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)

    return stage



def start_stage_execution(trigger, step_function_execution_arn, workflow_execution_id):
    execution_table_name = WORKFLOW_EXECUTION_TABLE_NAME

    try:
        execution_table = DYNAMO_RESOURCE.Table(execution_table_name)
        # lookup the workflow
        response = execution_table.get_item(
            Key={
                'id': workflow_execution_id
            },
            ConsistentRead=True)
        
        # lookup workflow defintiion we need to execute
        if "Item" in response:
            workflow_execution = response["Item"]
        else:
            workflow_execution = None
            raise ChaliceViewError(
                "Exception: workflow execution id '%s' not found" % workflow_execution_id)

        stage = workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]]
        stage['name'] = workflow_execution["current_stage"]
        stage['status'] = awsmas.STAGE_STATUS_EXECUTING
        stage['step_function_execution_arn'] = step_function_execution_arn

        workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]
                                                 ] = stage

        response = execution_table.update_item(
            Key={
                'id': workflow_execution_id
            },
            UpdateExpression='SET workflow.Stages.#stage = :stage',
            ExpressionAttributeNames={
                '#stage': workflow_execution["current_stage"]
            },
            ExpressionAttributeValues={
                ':stage': stage
            }
        )

    except Exception as e:

        stage = None
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)

    return stage


@app.route('/workflow/execution', cors=True, methods=['PUT'])
def update_workflow_execution():
    """ Update a workflow execution NOT IMPLEMENTED 

    XXX

    """
    stage = {"message":"UPDATE WORKFLOW EXECUTION NOT IMPLEMENTED"}
    return stage


@app.route('/workflow/execution', cors=True, methods=['GET'])
def list_workflow_executions():
    """ List all workflow executions

    Returns:
        A list of workflow executions.

    Raises:
        200: All workflow executions returned sucessfully.
        500: Internal server error 
    """

    table = DYNAMO_RESOURCE.Table(WORKFLOW_EXECUTION_TABLE_NAME)

    response = table.scan()
    workflow_executions = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        workflow_executions.extend(response['Items'])

    return workflow_executions


@app.route('/workflow/execution/{id}', cors=True, methods=['GET'])
def get_workflow_execution_by_id(id):
    """ Get a workflow executions by id

    Returns:
        A dictionary contianing the workflow execution.

    Raises:
        200: All workflow executions returned sucessfully.
        404: Not found
        500: Internal server error 
    """
    table = DYNAMO_RESOURCE.Table(WORKFLOW_EXECUTION_TABLE_NAME)
    workflow_execution = None
    response = table.get_item(
        Key={
            'id': id
        },
        ConsistentRead=True)

    if "Item" in response:
        workflow_execution = response["Item"]
    else:
        raise NotFoundError(
            "Exception: workflow execution '%s' not found" % id)

    return workflow_execution

@app.route('/workflow/execution/{id}', cors=True, methods=['DELETE'])
def delete_workflow_execution(id):
    """ Delete a workflow executions

    Returns:  

    Raises:
        200: Workflow execution deleted sucessfully.
        404: Not found
        500: Internal server error 
    """
    table = DYNAMO_RESOURCE.Table(WORKFLOW_EXECUTION_TABLE_NAME)

    try: 
        workflow_execution = None
        response = table.get_item(
            Key={
                'id': id
            },
            ConsistentRead=True)
        
        if "Item" in response:
            workflow_execution = response["Item"]
        else:
            raise NotFoundError(
                "Exception: workflow execution '%s' not found" % id)

        response = table.delete_item(
            Key={
                'id': id
            })      
    
    except Exception as e:

        workflow_execution = None
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)
    
    return workflow_execution



# ================================================================================================
#   ____          _                    ____                                    
#   / ___|   _ ___| |_ ___  _ __ ___   |  _ \ ___  ___  ___  _   _ _ __ ___ ___ 
#  | |  | | | / __| __/ _ \| '_ ` _ \  | |_) / _ \/ __|/ _ \| | | | '__/ __/ _ \
#  | |__| |_| \__ \ || (_) | | | | | | |  _ <  __/\__ \ (_) | |_| | | | (_|  __/
#   \____\__,_|___/\__\___/|_| |_| |_| |_| \_\___||___/\___/ \__,_|_|  \___\___|
#
# ================================================================================================


@app.lambda_function()
def workflow_custom_resource(event, context): 
    '''Handle Lambda event from AWS CloudFormation'''
    # Setup alarm for remaining runtime minus a second
    signal.alarm(int(context.get_remaining_time_in_millis() / 1000) - 1)

    # send_response(event, context, "SUCCESS",
    #                     {"Message": "Resource deletion successful!"})
    try:
        logger.info('REQUEST RECEIVED:\n %s', event)
        logger.info('REQUEST RECEIVED:\n %s', context)
        
        if event["ResourceProperties"]["ResourceType"] == "Operation":
            logger.info("Operation!!")
            operation_resource(event, context)

        elif event["ResourceProperties"]["ResourceType"] == "Stage":
            stage_resource(event, context)

        elif event["ResourceProperties"]["ResourceType"] == "Workflow":
            workflow_resource(event, context) 
        else:
            logger.info('FAILED!')
            send_response(event, context, "FAILED",
                        {"Message": "Unexpected resource type received from CloudFormation"})

        
    except Exception as e:

        logger.info('FAILED!')
        send_response(event, context, "FAILED", {
            "Message": "Exception during processing: '%s'" % e})

def operation_resource(event, context):

    operation = {}

    if event['RequestType'] == 'Create':
            logger.info('CREATE!')

            
            operation[event["ResourceProperties"]["name"]] = event["ResourceProperties"]

            #FIXME - boolean type comes in as tet from cloudformation - must decode string or take string for anabled parameter
            operation[event["ResourceProperties"]["name"]]["configuration"]["enabled"] = bool(operation[event["ResourceProperties"]["name"]]["configuration"]["enabled"])

            create_operation(operation)
            
            send_response(event, context, "SUCCESS",
                          {"Message": "Resource creation successful!", "name": event["ResourceProperties"]["name"]})

    elif event['RequestType'] == 'Update':
        logger.info('UPDATE!')
        send_response(event, context, "SUCCESS",
                        {"Message": "Resource update successful!"})
    elif event['RequestType'] == 'Delete':
        logger.info('DELETE!')

        name = event["ResourceProperties"]["name"]
        
        
        delete_operation(name)

        send_response(event, context, "SUCCESS",
                        {"Message": "Resource deletion successful!"})
    else:
        logger.info('FAILED!')
        send_response(event, context, "FAILED",
                        {"Message": "Unexpected event received from CloudFormation"})

    return operation

def stage_resource(event, context):
    stage = event["ResourceProperties"]

    if event['RequestType'] == 'Create':
            logger.info('CREATE!')

            create_stage(stage)
            
            send_response(event, context, "SUCCESS",
                          {"Message": "Resource creation successful!", "name": event["ResourceProperties"]["name"], "stateMachineArn":event["ResourceProperties"]["stateMachineArn"] })
            
    elif event['RequestType'] == 'Update':
        logger.info('UPDATE!')
        send_response(event, context, "SUCCESS",
                        {"Message": "Resource update successful!"})
    elif event['RequestType'] == 'Delete':
        logger.info('DELETE!')

        name = event["ResourceProperties"]["name"]
        
        delete_stage(name)

        send_response(event, context, "SUCCESS",
                        {"Message": "Resource deletion successful!"})
    else:
        logger.info('FAILED!')
        send_response(event, context, "FAILED",
                        {"Message": "Unexpected event received from CloudFormation"})

    return stage

def workflow_resource(event, context):
    workflow = event["ResourceProperties"]

    logger.info(json.dumps(workflow))

    if event['RequestType'] == 'Create':
            logger.info('CREATE!')

            workflow["Stages"] = json.loads(event["ResourceProperties"]["Stages"])

            create_workflow("custom-resource", workflow)

            send_response(event, context, "SUCCESS",
                          {"Message": "Resource creation successful!"})
    elif event['RequestType'] == 'Update':
        logger.info('UPDATE!')
        send_response(event, context, "SUCCESS",
                        {"Message": "Resource update successful!"})
    elif event['RequestType'] == 'Delete':
        logger.info('DELETE!')

        name = event["ResourceProperties"]["name"]
        
        delete_workflow(name)

        send_response(event, context, "SUCCESS",
                        {"Message": "Resource deletion successful!"})
    else:
        logger.info('FAILED!')
        send_response(event, context, "FAILED",
                        {"Message": "Unexpected event received from CloudFormation"})

    return workflow


def send_response(event, context, response_status, response_data):
    '''Send a resource manipulation status response to CloudFormation'''
    response_body = json.dumps({
        "Status": response_status,
        "Reason": "See the details in CloudWatch Log Stream: " + context.log_stream_name,
        "PhysicalResourceId": context.log_stream_name,
        "StackId": event['StackId'],
        "RequestId": event['RequestId'],
        "LogicalResourceId": event['LogicalResourceId'],
        "Data": response_data
    })

    logger.info('ResponseURL: %s', event['ResponseURL'])
    logger.info('ResponseBody: %s', response_body)

    opener = build_opener(HTTPHandler)
    request = Request(event['ResponseURL'], data=response_body.encode('utf-8'))
    request.add_header('Content-Type', '')
    request.add_header('Content-Length', len(response_body))
    request.get_method = lambda: 'PUT'
    response = opener.open(request)
    logger.info("Status code: %s", response.getcode())
    logger.info("Status message: %s", response.msg)


def timeout_handler(_signal, _frame):
    '''Handle SIGALRM'''
    raise Exception('Time exceeded')
                                                                              
