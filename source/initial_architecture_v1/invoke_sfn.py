import time
import boto3
from botocore.exceptions import ClientError


table_name = 'controlplane-test'

sfn = boto3.client('stepfunctions')
ddb = boto3.resource('dynamodb')
control_plane_table = ddb.Table(table_name)

# Need to sort out the correct way to have ddb libs called
ddb_client = boto3.client('dynamodb')

# These will be stored in a field in the DB and will be passed in as part of the API

preprocess_arn = 'arn:aws:states:us-east-1:764127651952:stateMachine:mas_test_preprocess'
analysis_arn = 'arn:aws:states:us-east-1:764127651952:stateMachine:media-analysis-state-machine-1'

default_workflow = {'preprocess': {'arn': preprocess_arn, 'status': 'NOT_STARTED'}, 'analysis': {'arn': analysis_arn, 'status': 'NOT_STARTED'} }


def create_record(event_info, job_id, execution_info):
    control_plane_table.put_item(Item={
        'job_id': job_id,
        'event_info': event_info,
        'execution_info': execution_info
    })


# Need to cleanup the input of this function since i'm passing job in at 2 places

def invoke_step_functions(state_machine_arn, job_id, params):
    timestamp = str(time.time()).split('.')[1]

    execution_name = timestamp + '-' + job_id
    try:
        response = sfn.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=params
        )

        return response['executionArn']
    except ClientError as e:
        print(e)
        return 'failed'


# Might think about breaking this function out into two functions: start_stage, complete_stage

def update_job_data(job_id, params):
    
    # Need to add well rounded parsing of params here, statically parsing below

    stage = list(params.keys())[0]
    status = str(params[stage])
    try:
        execution_arn = str(params['execution_arn'])

        ddb_client.update_item(
            TableName=table_name,
            Key={'job_id': {'S': job_id}},
            UpdateExpression='SET #exc_info.#stage.#status = :statusVal, #exc_info.#stage.#exc_arn = :arnVal',
            ExpressionAttributeNames={'#exc_info': 'execution_info', '#stage': stage, '#status': 'status',
                                      '#exc_arn': 'exc_arn'},
            ExpressionAttributeValues={':statusVal': {"S": status}, ':arnVal': {"S": execution_arn}}
        )

    # Again need to have MUCH better exception handling here, not sure what the correct boto execption would be here
    except Exception:
        print('This is just a stage status completion')
        ddb_client.update_item(
            TableName=table_name,
            Key={'job_id': {'S': job_id}},
            UpdateExpression='SET #exc_info.#stage.#status = :statusVal',
            ExpressionAttributeNames={'#exc_info': 'execution_info', '#stage': stage, '#status': 'status'},
            ExpressionAttributeValues={':statusVal': {"S": status}}
        )


# Need to fill this out to be call at the beginning of each step function to get job params

def get_job_data(job_id):
    response = ddb_client.get_item(
        TableName=table_name,
        Key={
            "job_id": {"S": job_id}
        },
        AttributesToGet=['event_info']
    )

    return response['Item']['event_info']['S']

def lambda_handler(event, context):

    print(event)

    # Need to refactor this try/catch block to have better handling to direct to correct functions...

    try:

        # Initial upload

        if event['Records'][0]['eventSource'] == 'aws:s3':
            job_id = context.aws_request_id
            media_key = event['Records'][0]['s3']['object']['key']
            # omitting these value 'owner_id': , 'object_id':
            execution_info = default_workflow
            event_info = '{{ "job_id": "{job_id}", "key": "{media_key}", "file_type": "{file_type}", "size": "{size}", "file_name": "{file_name}", "bucket": "{bucket}" }}'.format(
            media_key=media_key, file_type=media_key.split('.')[1], file_name=media_key,
            size=event['Records'][0]['s3']['object']['size'], bucket=event['Records'][0]['s3']['bucket']['name'],
            job_id=job_id)
            create_record(event_info, job_id, execution_info)

            first_key = list(default_workflow.keys())[0]
            first_step_arn = default_workflow[first_key]['arn']

            # Should add exception handling here to only update job data if job invocation is successful
            job_invocation = invoke_step_functions(first_step_arn, job_id, event_info)

            if job_invocation == 'failed':
                print('Unable to invoke')
                print(job_invocation)
            else:

                # Params to pass for updating record
                status_update = {first_key: 'IN_PROGRESS', 'execution_arn': job_invocation}
                update_job_data(job_id, status_update)

    # This is seriously so bad, please go back brandon and clean this up

    except Exception:
        # Handle everything else other than the first upload
        if 'job_id' in event:

            '''Manually setting the status update here since my preprocess step doesn't do anything, 
            need to update this to be dynamic'''

            stage_completion = {'preprocess': 'COMPLETE'}
            update_job_data(event['job_id'], stage_completion)

            # Calling next stage and setting as IN_PROGRESS, again doing this static for now, future would be pull record from DB

            params = get_job_data(event['job_id'])

            print(params)

            job_invocation = invoke_step_functions(analysis_arn, event['job_id'], params)

            if job_invocation == 'failed':
                print('Unable to invoke')
                print(job_invocation)
            else:
                # Params to pass for updating record
                print('Kicked off next stage')
                status_update = {'analysis': 'IN_PROGRESS', 'execution_arn': job_invocation}
                update_job_data(event['job_id'], status_update)



