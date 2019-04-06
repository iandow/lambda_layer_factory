import boto3
from outputHelper import OutputHelper
from outputHelper import MasExecutionError

comprehend = boto3.client('comprehend')
s3 = boto3.client('s3')

operator_name = 'comprehend'
output_object = OutputHelper(operator_name)


def lambda_handler(event, context):
    print("We got this event:\n", event)
    try:
        job_id = event["metadata"]["comprehend_job_id"]
    except KeyError:
        output_object.update_status("Error")
        output_object.update_metadata(comprehend_error="No valid job id")
        raise MasExecutionError(output_object.return_output_object())
    try:
        response = comprehend.list_key_phrases_detection_jobs(
            Filter={
                'JobName': job_id,
            },
        )
    except Exception as e:
        output_object.update_status("Error")
        output_object.update_metadata(comprehend_error="Unable to get response from comprehend: {e}".format(e=str(e)))
        raise MasExecutionError(output_object.return_output_object())
    else:
        print(response)
        comprehend_status = response["KeyPhrasesDetectionJobPropertiesList"][0]["JobStatus"]
        if comprehend_status == "SUBMITTED" or comprehend_status == "IN_PROGRESS":
            output_object.update_metadata(comprehend_job_id=job_id)
            output_object.update_status("Executing")
            return output_object.return_output_object()
        elif comprehend_status == "COMPLETED":
            output_uri = response["KeyPhrasesDetectionJobPropertiesList"]["OutputDataConfig"][0]["S3Uri"]
            # TODO: Find a better way to split the uri, below will only work with 1 prefix, e.g. /metadata/outputuri
            bucket = output_uri.split("/")[4]
            key = output_uri.split("/")[5] + output_uri.split("/")[6]
            output_object.update_metadata(comprehend_job_id=job_id, output_uri=output_uri)
            output_object.update_media("text", bucket, key)
            output_object.update_status("Complete")
            return output_object.return_output_object()
        else:
            output_object.update_status("Error")
            output_object.update_metadata(comprehend_job_id=job_id, comprehend_error="comprehend returned as failed: {e}".format(e=str(response["KeyPhrasesDetectionJobPropertiesList"]["Message"])))
            raise MasExecutionError(output_object.return_output_object())
