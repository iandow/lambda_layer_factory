import boto3
from outputHelper import OutputHelper
from outputHelper import MasExecutionError

polly = boto3.client("polly")
s3 = boto3.client("s3")

operator_name = "polly"
output_object = OutputHelper(operator_name)

def lambda_handler(event, context):

    print("We got this event:\n", event)

    try:
        task_id = event["metadata"]["polly_job_id"]
    except KeyError:
        output_object.update_status("Error")
        output_object.update_metadata(translate_error="No valid job id")
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
            output_object.update_metadata(polly_job_id=polly_job_id)
            output_object.update_status("Executing")
            return output_object.return_output_object()
        elif polly_status == "completed":
            uri = polly_response["SynthesisTask"]["OutputUri"]
            file = uri.split("/")[5]
            folder = uri.split("/")[4]
            bucket = uri.split("/")[3]
            key = folder + "/" + file

            output_object.update_metadata(polly_job_id=task_id)
            output_object.update_media("audio", bucket, key)
            output_object.update_status("Complete")
            return output_object.return_output_object()

        elif polly_status == "scheduled":
            polly_job_id = polly_response["SynthesisTask"]["TaskId"]
            output_object.update_metadata(polly_job_id=polly_job_id)
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


