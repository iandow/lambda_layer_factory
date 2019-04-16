import os
import boto3
from awsmie import OutputHelper
from awsmie import MasExecutionError

comprehend = boto3.client('comprehend')
s3 = boto3.client('s3')

comprehend_role = os.environ['comprehendRole']
region = os.environ['AWS_REGION']

operator_name = 'comprehend'
output_object = OutputHelper(operator_name)


def lambda_handler(event, context):

    print("We got this event:\n", event)

    job_id = operator_name + "-" + str(event["workflow_execution_id"])

    try:
        bucket = event["input"]["media"]["text"]["s3bucket"]
        key = event["input"]["media"]["text"]["s3key"]
        uri = "s3://" + bucket + '/' + key
        output_uri = "s3://" + bucket + '/' + "metadata/"
    except KeyError:
        output_object.update_status("Error")
        output_object.update_metadata(comprehend_error="No valid inputs")
        raise MasExecutionError(output_object.return_output_object())

    try:
        comprehend.start_key_phrases_detection_job(
            InputDataConfig={
                'S3Uri': uri,
                'InputFormat': 'ONE_DOC_PER_FILE'
            },
            OutputDataConfig={
                'S3Uri': output_uri
            },
            DataAccessRoleArn=comprehend_role,
            JobName=job_id,
            LanguageCode='en'
        )

    except Exception as e:
        output_object.update_status("Error")
        output_object.update_metadata(comprehend_error="Unable to get response from comprehend: {e}".format(e=str(e)))
        raise MasExecutionError(output_object.return_output_object())
    else:
        comprehend_job_id = job_id
        output_object.update_metadata(comprehend_job_id=comprehend_job_id, output_uri=output_uri)
        output_object.update_status('Executing')
        return output_object.return_output_object()


