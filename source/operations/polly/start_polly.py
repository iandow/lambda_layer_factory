import boto3
from mas_helper import OutputHelper
from mas_helper import MasExecutionError

polly = boto3.client('polly')
s3 = boto3.client('s3')

operator_name = 'polly'
output_object = OutputHelper(operator_name)

# TODO: Move voiceid to a user configurable variable

def lambda_handler(event, context):
    print("We got this event:\n", event)

    try:
        workflow_id = event["workflow_execution_id"]
    except KeyError as e:
        output_object.update_status("Error")
        output_object.update_metadata(polly_error="Missing a required metadata key {e}".format(e=e))
        raise MasExecutionError(output_object.return_output_object())
    try:
        asset_id = event["asset_id"]
    except KeyError:
        print('No asset id passed along with this workflow')
        asset_id = ''

    try:
        bucket = event["input"]["media"]["text"]["s3bucket"]
        key = event["input"]["media"]["text"]["s3key"]
    except KeyError:
        output_object.update_status("Error")
        output_object.update_metadata(polly_error="No valid inputs")
        raise MasExecutionError(output_object.return_output_object())
    try:
        s3_response = s3.get_object(Bucket=bucket, Key=key)
        translation = s3_response["Body"].read().decode("utf-8")
    except Exception as e:
        output_object.update_status("Error")
        output_object.update_metadata(polly_error="Unable to read translation from S3: {e}".format(e=str(e)))
        raise MasExecutionError(output_object.return_output_object())

    print("Translation received from S3:\n", translation)

    try:
        polly_response = polly.start_speech_synthesis_task(
            OutputFormat='mp3',
            OutputS3BucketName=bucket,
            OutputS3KeyPrefix='audio/translation.mp3',
            Text=translation,
            TextType='text',
            VoiceId='Maxim'
        )

    except Exception as e:
        output_object.update_status("Error")
        output_object.update_metadata(polly_error="Unable to get response from polly: {e}".format(e=str(e)))
        raise MasExecutionError(output_object.return_output_object())
    else:
        polly_job_id = polly_response['SynthesisTask']['TaskId']
        output_object.update_metadata(polly_job_id=polly_job_id, workflow_id=workflow_id, asset_id=asset_id)
        output_object.update_status('Executing')
        return output_object.return_output_object()


