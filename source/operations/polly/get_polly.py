import boto3

from awsmie import OutputHelper
from awsmie import MasExecutionError
from awsmie import DataPlane

polly = boto3.client("polly")
s3 = boto3.client("s3")

operator_name = "polly"
output_object = OutputHelper(operator_name)

def lambda_handler(event, context):

    print("We got this event:\n", event)

    try:
        task_id = event["metadata"]["polly_job_id"]
        workflow_id = event["metadata"]["workflow_id"]
        asset_id = event["metadata"]["asset_id"]
    except KeyError as e:
        output_object.update_status("Error")
        output_object.update_metadata(transcribe_error="Missing a required metadata key {e}".format(e=e))
        raise MasExecutionError(output_object.return_output_object())
    try:
        polly_response = polly.get_speech_synthesis_task(
            TaskId=task_id
        )
    except Exception as e:
        output_object.update_status("Error")
        output_object.update_metadata(polly_error="Unable to get response from polly: {e}".format(e=str(e)))
        raise MasExecutionError(output_object.return_output_object())
    else:
        polly_status = polly_response["SynthesisTask"]["TaskStatus"]
        print("The status from polly is:\n", polly_status)
        if polly_status == "inProgress":
            polly_job_id = polly_response["SynthesisTask"]["TaskId"]
            output_object.update_metadata(polly_job_id=polly_job_id, asset_id=asset_id, workflow_id=workflow_id)
            output_object.update_status("Executing")
            return output_object.return_output_object()
        elif polly_status == "completed":
            uri = polly_response["SynthesisTask"]["OutputUri"]
            file = uri.split("/")[5]
            folder = uri.split("/")[4]
            bucket = uri.split("/")[3]
            key = folder + "/" + file

            # persist polly media object

            dataplane = DataPlane(asset_id, workflow_id)
            persist_media = dataplane.persist_media(s3bucket=bucket, s3key=key)
            if persist_media["status"] == "failed":
                output_object.update_status("Error")
                output_object.update_metadata(
                    polly_error="Unable to persist media for asset: {asset}".format(asset=asset_id),
                    polly_job_id=task_id)
                raise MasExecutionError(output_object.return_output_object())
            else:
                new_bucket = persist_media['s3bucket']
                new_key = persist_media['s3key']

                output_object.update_metadata(polly_job_id=task_id)
                output_object.update_media("audio", new_bucket, new_key)
                output_object.update_status("Complete")

                return output_object.return_output_object()

        elif polly_status == "scheduled":
            output_object.update_metadata(polly_job_id=task_id, asset_id=asset_id, workflow_id=workflow_id)
            output_object.update_status("Executing")
            return output_object.return_output_object()

        elif polly_status == "failed":
            output_object.update_status("Error")
            output_object.update_metadata(polly_error="Polly returned as failed: {e}".format(e=str(polly_response["SynthesisTask"]["TaskStatusReason"])))
            raise MasExecutionError(output_object.return_output_object())
        else:
            output_object.update_status("Error")
            output_object.update_metadata(polly_error="Polly returned as failed: {e}".format(e=str(polly_response["SynthesisTask"]["TaskStatusReason"])))
            raise MasExecutionError(output_object.return_output_object())


