import os
import boto3

region = os.environ['AWS_REGION']
transcribe = boto3.client("transcribe")

from mas_helper import OutputHelper
from mas_helper import MasExecutionError

operator_name = 'transcribe'
output_object = OutputHelper(operator_name)

# TODO: More advanced exception handling, e.g. using boto clienterrors and narrowing exception scopes


def lambda_handler(event, context):
        workflow_id = str(event["workflow_execution_id"])
        job_id = "transcribe" + "-" + workflow_id
        valid_types = ["mp3", "mp4", "wav", "flac"]
        optional_settings = {}

        # Adding in exception block for now since we aren't guaranteed an asset id will be present, should remove later
        try:
            asset_id = event['asset_id']
        except KeyError as e:
            print("No asset id passed in with this workflow", e)
            asset_id = ''

        try:
            bucket = event["input"]["media"]["audio"]["s3bucket"]
            key = event["input"]["media"]["audio"]["s3key"]
            file_type = key.split(".")[1]
        # TODO: Do we want to add support for video?
        except KeyError:
            bucket = event["input"]["media"]["video"]["s3bucket"]
            key = event["input"]["media"]["video"]["s3key"]
            file_type = key.split(".")[1]
        except Exception:
            output_object.update_status("Error")
            output_object.update_metadata(transcribe_error="No valid inputs")
            raise MasExecutionError(output_object.return_output_object())
        if file_type not in valid_types:
            output_object.update_status("Error")
            output_object.update_metadata(transcribe_error="Not a valid file type")
            raise MasExecutionError(output_object.return_output_object())
        try:
            custom_vocab = event["configuration"]["transcribe"]["vocabularyName"]
            optional_settings["VocabularyName"] = custom_vocab
        except KeyError:
            # No custom vocab
            pass
        try:
            language_code = event["configuration"]["transcribe"]["transcribeLanguage"]
        except KeyError:
            output_object.update_status("Error")
            output_object.update_metadata(transcribe_error="No language code defined")
            raise MasExecutionError(output_object.return_output_object())

        media_file = 'https://s3.' + region + '.amazonaws.com/' + bucket + '/' + key

        try:
            response = transcribe.start_transcription_job(
                TranscriptionJobName=job_id,
                LanguageCode=language_code,
                Media={
                    "MediaFileUri": media_file
                },
                MediaFormat=file_type,
                Settings=optional_settings
            )
            print(response)
        except Exception as e:
            output_object.update_status("Error")
            output_object.update_metadata(transcribe_error=str(e))
            raise MasExecutionError(output_object.return_output_object())
        else:
            if response["TranscriptionJob"]["TranscriptionJobStatus"] == "IN_PROGRESS":
                output_object.update_status("Executing")
                output_object.update_metadata(transcribe_job_id=job_id, asset_id=asset_id, workflow_id=workflow_id)
                return output_object.return_output_object()
            elif response["TranscriptionJob"]["TranscriptionJobStatus"] == "FAILED":
                output_object.update_status("Error")
                output_object.update_metadata(transcribe_job_id=job_id, transcribe_error=str(response["TranscriptionJob"]["FailureReason"]))
                raise MasExecutionError(output_object.return_output_object())
            elif response["TranscriptionJob"]["TranscriptionJobStatus"] == "COMPLETE":
                output_object.update_status("Executing")
                output_object.update_metadata(transcribe_job_id=job_id, asset_id=asset_id, workflow_id=workflow_id)
                return output_object.return_output_object()
            else:
                output_object.update_status("Error")
                output_object.update_metadata(transcribe_job_id=job_id,
                                              transcribe_error="Unhandled error for this job: {job_id}".format(job_id=job_id))
                raise MasExecutionError(output_object.return_output_object())
