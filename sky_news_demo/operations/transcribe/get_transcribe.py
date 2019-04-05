import os
import boto3
import urllib3

region = os.environ['AWS_REGION']
transcribe = boto3.client("transcribe")

from outputHelper import OutputHelper
from outputHelper import MasExecutionError

operator_name = 'transcribe'
output_object = OutputHelper(operator_name)

# TODO: More advanced exception handling, e.g. using boto clienterrors and narrowing exception scopes


def lambda_handler(event, context):
    try:
        job_id = event["metadata"]["transcribe_job_id"]
        try:
            response = transcribe.get_transcription_job(
                TranscriptionJobName=job_id
            )
            print(response)
        except Exception as e:
            output_object.update_status("Error")
            output_object.update_metadata(transcribe_error=str(e), transcribe_job_id=job_id)
            raise MasExecutionError(output_object.return_output_object())
        else:
            if response["TranscriptionJob"]["TranscriptionJobStatus"] == "IN_PROGRESS":
                output_object.update_status("Executing")
                output_object.update_metadata(transcribe_job_id=job_id)
                return output_object.return_output_object()
            elif response["TranscriptionJob"]["TranscriptionJobStatus"] == "FAILED":
                output_object.update_status("Error")
                output_object.update_metadata(transcribe_job_id=job_id, transcribe_error=str(response["TranscriptionJob"]["FailureReason"]))
                raise MasExecutionError(output_object.return_output_object())
            elif response["TranscriptionJob"]["TranscriptionJobStatus"] == "COMPLETED":
                output_object.update_status("Complete")
                transcribe_uri = response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                http = urllib3.PoolManager()
                transcription = http.request('GET', transcribe_uri)
                transcription_data = transcription.data.decode("utf-8")

                output_object.update_metadata(transcribe_job_id=job_id, transcription=transcription_data)
                return output_object.return_output_object()
            else:
                output_object.update_status("Error")
                output_object.update_metadata(transcribe_error="Unable to determine status")
                raise MasExecutionError(output_object.return_output_object())

    except Exception as e:
        output_object.update_status("Error")
        output_object.update_metadata(transcribe_error=str(e))
        raise MasExecutionError(output_object.return_output_object())
