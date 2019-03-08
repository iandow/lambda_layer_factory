from chalice import Chalice
from chalice import NotFoundError, BadRequestError, ChaliceViewError, Response
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
from chalicelib import awsmas

APP_NAME = "workflow-api"
API_STAGE = "dev"
app = Chalice(app_name=APP_NAME)
app.debug = True

# Setup logging
logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)

WORKFLOW_TABLE_NAME = os.environ["WORKFLOW_TABLE_NAME"]
#STAGE_TABLE_NAME = os.environ["STAGE_TABLE_NAME"]
STAGE_TABLE_NAME = "mas-workflowStage"
#OPERATION_TABLE_NAME = os.environ["OPERATION_TABLE_NAME"]
OPERATION_TABLE_NAME = "mas-workflowOperation"
WORKFLOW_EXECUTION_TABLE_NAME = os.environ["WORKFLOW_EXECUTION_TABLE_NAME"]
STAGE_EXECUTION_QUEUE_URL = os.environ["STAGE_EXECUTION_QUEUE_URL"]

# FIXME - need create stage API and custom resource to break circular dependency
PREPROCESS_STATE_MACHINE_ARN 
    = "arn:aws:states:us-east-1:526662735483:stateMachine:media-analysis-preprocess-state-machine-2"
ANALYSIS_STATE_MACHINE_ARN 
    = "arn:aws:states:us-east-1:526662735483:stateMachine:analysis-state-machine"
POSTPROCESS_STATE_MACHINE_ARN 
    = "arn:aws:states:us-east-1:526662735483:stateMachine:media-analysis-preprocess-state-machine-2"

# DynamoDB
DYNAMO_CLIENT = boto3.client("dynamodb")
DYNAMO_RESOURCE = boto3.resource("dynamodb")

# Step Functions
SFN_CLIENT = boto3.client('stepfunctions')

# Simple Queue Service
SQS_RESOURCE = boto3.resource('sqs')
SQS_CLIENT = boto3.client('sqs')

# Environment

DEFAULT_WORKFLOW_SQS = {
    "name": "MAS-Pipeline",
    "StartAt": "Preprocess",
    "Stages": {
        "Preprocess": {
            "Type": "Preprocess",
            "Resource": STAGE_EXECUTION_QUEUE_URL,
            "StateMachine": PREPROCESS_STATE_MACHINE_ARN,
            "Next": "Analysis"
        },
        "Analysis": {
            "Type": "Analysis",
            "Resource": STAGE_EXECUTION_QUEUE_URL,
            "StateMachine": ANALYSIS_STATE_MACHINE_ARN,
            "End": True
        }
    }
}

# Helper class to convert a DynamoDB item to JSON.

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


@app.route('/')
def index():
    return {'hello': 'world'}

##############################################################################
# Operations
##############################################################################

@app.route('/workflow/operation', cors=True, methods=['POST'])
def create_operation(): 
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
        "operation-name": {
            "configuration" : {
                "mediaType": "video",
                "enabled:": True,
                "configruation1": "value1",
                "configruation2": "value2",
                ...
            },
            "input": {
                "metadata": {
                    "name":"input1",
                    "type":"string",
                    "required": false
                }
            },
            "stateMachineArn":arn,
            "stateMachineExecutionRoleArn":arn

        }

    Returns:
        A dict mapping keys to the corresponding operation created including 
        the ASL for the duplicated state machine a guid and a create time.

    Raises:
        200: The operation was created successfully.
        400: Bad Request - the input state machine ARN was not found or the 
             state machine ASL is invalid
        500: Internal server error 
    """
    table_name = OPERATION_TABLE_NAME

    try:
        table = DYNAMO_RESOURCE.Table(table_name)

        print(app.current_request.json_body)

        operation = app.current_request.json_body

        # save operation configuration

        print(json.dumps(operation))
        for k, v in operation.items():
            print(k, v)

        name = k
        if "stateMachineArn" in operation:

            response = SFN_CLIENT.describe_state_machine(
                stateMachineArn=operation[name]["stateMachineArn"]
                )

            operation["stateMachineASL"] = response["definition"]
            
        operation["name"] = name
        
        table.put_item(Item=operation)

    except SFN_CLIENT.exceptions.NotFoundException as e:
        raise BadRequestError("State machine ARN {} not found. Error: {}"
            .format(operation[name]["stateMachineArn"], e))

    except Exception as e:
        logger.info("Exception {}".format(e))
        operation = None
        raise ChaliceViewError("Exception '%s'" % e)

    return operation
    

@app.route('/workflow/operation', cors=True, methods=['PUT'])
def update_operation(): 
    operation = {}
    return operation

@app.route('/workflow/operation', cors=True, methods=['GET'])
def list_operations():
    """ List all operators

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
def get_operations_by_name(name):
    """ Get an operation definition by name

    Returns:
        A dictionary contianing the operation definition.

    Raises:
        200: All operations returned sucessfully.
        404: Not found
        500: Internal server error 
    """  
    operation = {}
    return operation

###############################################################################
# Workflows
###############################################################################

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

    workflow_table_name = WORKFLOW_TABLE_NAME

    try:
        workflow_table = DYNAMO_RESOURCE.Table(workflow_table_name)

        print(app.current_request.json_body)

        workflow_configuration = app.current_request.json_body

        

        # temporary scaffolding - hard code
        workflow = DEFAULT_WORKFLOW_SQS


        # save workflow configuration

        workflow = initialize_workflow_execution(
            workflow, workflow_configuration)

        print(json.dumps(workflow))
        #workflow["createTime"] = int(time.time())
        workflow_table.put_item(Item=workflow)

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

# Build a stage
# In:
#    {
#    "name":"",
#    "Operations[operation1, operation2, operation3, ...]
#     }

TEMP_ROLE = "arn:aws:iam::526662735483:role/mas-workflow-StageExecutionRole-1NQQVDCXLSXGN"

################################################################################################
# Stages
################################################################################################

@app.route('/workflow/stage', cors=True, methods=['POST'])
def create_stage():

    stage_table_name = STAGE_TABLE_NAME
    operation_table_name = OPERATION_TABLE_NAME    

    

    try:
        stage_table = DYNAMO_RESOURCE.Table(stage_table_name)
        operation_table = DYNAMO_RESOURCE.Table(operation_table_name)

        print(app.current_request.json_body)

        stage = app.current_request.json_body
        name = stage["name"]

        # Build the stage state machine
        stageAsl = {
            "StartAt": "Preprocess Media",
            "States": {
                "Complete Stage": {
                    "Type": "Task",
                        "Resource": "arn:aws:lambda:us-east-1:526662735483:function:mas-workflow-MediaAnalysi-CompleteStageExecutionLa-1CE5AAOFHDZXM",
                        "End": True
                }        
            }
        }
        stageAsl["StartAt"] = name
        stageAsl["States"][name] = {
                "Type": "Parallel",
                "Next": "Complete Stage",
                "ResultPath": "$.stage",
                "Branches": [
                ]
            }

        # Add a branch for each operation   
        for op in stage["operations"]:
        # lookup base workflow
            response = operation_table.get_item(
                Key={
                    'name': op
                })

            if "Item" in response:
                operation = response["Item"]
            else:
                stage = None
                raise ChaliceViewError(
                    "Exception: operation '%s' not found" % operation)

            stageAsl["States"][name]["Branches"].append(json.loads(operation["stateMachineASL"]))

        print (json.dumps(stageAsl))

        response = SFN_CLIENT.create_state_machine(
            name=name,
            definition=json.dumps(stageAsl),
            roleArn=TEMP_ROLE
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
    stage = {}
    return stage

@app.route('/workflow/stage', cors=True, methods=['GET'])
def list_stages(): 
    stages = []
    return stages

@app.route('/workflow/stage/{name}', cors=True, methods=['GET'])
def get_stage_by_name(name): 
    stage = {}
    return stage


# ================================================================================================
# Workflow Executions
# ================================================================================================

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

        # FIXME - construct stages from stage table at runtime to get latest defintion

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
                "workflow_execution_id": workflow_execution["id"],
                "stage": workflow_execution["workflow"]["Stages"][current_stage]
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

@app.route('/workflow/{workflowId}')
def get_workflow_by_id():
    response = {}
    return response


@app.route('/workflow')
def get_workflow():
    response = {}
    return response

@app.route('/workflow/execution/nextstage', cors=True, methods=['POST'])
def execute_next_stage():
    
    stage = app.current_request.json_body
    print(stage)
    stage = execute_stage(stage)

    return stage  

@app.lambda_function()
def test_execute_stage_lambda(event, context):
    
    try:
        print("EVENT")
        print(json.dumps(event))

        for record in event["Records"]:
            message = json.loads(record["body"])
            print(message)

        stage = execute_stage(message)
    
    except Exception as e:
        #stage = complete_stage_execution(
        #        "workflow", STAGE_STATUS_ERROR, outputs, workflow_execution_id)
        #stage["exception"] = str(e)
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)

    return stage


def execute_stage(input_stage):

    try:
        workflow_execution_id = input_stage["workflow_execution_id"]

        stage = get_stage_for_execution("workflow", workflow_execution_id)
        stage["workflow_execution_id"] = workflow_execution_id 

        # FIXME check for duplicate SQS messages - SQS messages have AT LEAST ONCE delivery semantics
        # we only want to process an operation once since it could be expensive.
        # State machine will give error when executing same stage with same execution id, maybe use this?:
        # An error occurred (ExecutionAlreadyExists) when calling the StartExecution operation: Execution Already Exists: 'arn:aws:states:us-east-1:526662735483:execution:media-analysis-preprocess-state-machine-1:1c2b2471-a451-49b5-a6f7-12618b955d74
        #    
        
        print(stage)
        if stage["name"] == "Preprocess":
            sfn_input = map_preprocess_sfn_input(stage)
        elif stage["name"] == "Analysis":
            sfn_input = map_analysis_sfn_input(stage)
        
        print(sfn_input)
        response = SFN_CLIENT.start_execution(
            stateMachineArn=stage["StateMachine"],
            name=stage["name"]+workflow_execution_id,
            input=json.dumps(sfn_input)
        )

        stage["stepFunctionExecutionArn"] = response['executionArn']

        print("REGISTER STEP FUNCTION ARN WITH CONTROL PLANE")
        stage = start_stage_execution(
            "workflow", stage["stepFunctionExecutionArn"], workflow_execution_id)

    except Exception as e:
        #stage = complete_stage_execution(
        #        "workflow", STAGE_STATUS_ERROR, outputs, workflow_execution_id)
        #stage["exception"] = str(e)
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)

    return stage

# FIXME: Temporary to map stage structure to step function input structure
def map_analysis_sfn_input(stage):
    sfn_input = {
        "file_type": "mp4",
        "eventSource": "media-analysis",
        "configuration": {
            "Video-Label": "enabled",
            "Video-Celeb": "disabled",
            "Video-Face": "disabled",
            "Video-Face-Match": "disabled",
            "Video-Person": "disabled"
        }
    }

    sfn_input["outputs"] = {}
    sfn_input["key"] = stage["input"]["media"]["video"]["s3key"]
    sfn_input["bucket"] = stage["input"]["media"]["video"]["s3bucket"]
    sfn_input["status"] = stage["status"]
    sfn_input["workflow_execution_id"] = stage["workflow_execution_id"]

    return sfn_input

# FIXME: Temporary map preprocess stage output to stage expected output
def map_analysis_sfn_output(sfn_output):
    stage_output = {
        "media":{
            "audio": {
            }
        },
        "metadata": {}
    }

    return stage_output

# FIXME: Temporary to map stage structure to step function input structure
def map_preprocess_sfn_input(stage):
    sfn_input = {
        "file_type": "mp4",
        "eventSource": "media-analysis",
        "stage": {
            "stage": "preprocess"
        },
        "lambda": {
            "service_name": "media_convert",
            "function_name": "start_media_convert"
        }
    }

    sfn_input["outputs"] = {}
    sfn_input["key"] = stage["input"]["media"]["video"]["s3key"]
    sfn_input["bucket"] = stage["input"]["media"]["video"]["s3bucket"]
    sfn_input["status"] = stage["status"]
    sfn_input["workflow_execution_id"] = stage["workflow_execution_id"]

    return sfn_input

# FIXME: Temporary map preprocess stage output to stage expected output
def map_preprocess_sfn_output(sfn_output):
    stage_output = {
        "media":{
            "audio": {
            }
        },
        "metadata": {}
    }

    stage_output["media"]["audio"]["s3key"] = sfn_output["key"]
    #stage_output["media"]["audio"]["s3bucket"] = sfn_output["s3bucket"]
    stage_output["media"]["audio"]["destination"] = sfn_output["destination"]
    stage_output["media"]["audio"]["file_type"] = sfn_output["file_type"]

    return stage_output

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

        #if (workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]] != )
        stage = workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]]
        stage['name'] = workflow_execution["current_stage"]
        stage["workflow_execution_id"] = workflow_execution_id

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

        if stage["name"] == "Preprocess":
            print(json.dumps(outputs))
            stage_outputs = map_preprocess_sfn_output(outputs)
            print("MAPPED OUTPUTS")
            print(json.dumps(stage_outputs))
        elif stage["name"] == "Analysis":
            print(json.dumps(outputs))
            stage_outputs = map_analysis_sfn_output(outputs)
            print("MAPPED OUTPUTS")
            print(json.dumps(stage_outputs))

        workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]
                                                 ]["status"] = status


        print(workflow_execution["workflow"]["Stages"]
              [workflow_execution["current_stage"]])

        workflow_execution["workflow"]["Stages"][workflow_execution["current_stage"]
                                                 ]["outputs"] = stage_outputs

        print(json.dumps(stage_outputs))

        # update workflow globals
        if "media" in stage_outputs:
            for mediaType in stage_outputs["media"].keys():
                # replace media with trasformed or created media from this stage
                print(mediaType)
                workflow_execution['globals']["media"][mediaType] = stage_outputs["media"][mediaType]

        if "metadata" not in workflow_execution['globals']:
            workflow_execution['globals']["metadata"] = {}

        if "metadata" in stage_outputs:
            for key in stage_outputs["metadata"].keys():
                print(key)
                workflow_execution['globals']["metadata"][key] = stage_outputs["metadata"][key]

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
                raise ChaliceViewError(
                    "Exception: unable to queue work item '%s'" % e)

    except Exception as e:
        workflow_execution["status"] = WORKFLOW_STATUS_ERROR
        logger.info("Exception {}".format(e))
        raise ChaliceViewError("Exception: '%s'" % e)
    return workflow_execution



