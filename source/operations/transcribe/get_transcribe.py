import os
import boto3
import urllib3
import json

region = os.environ['AWS_REGION']
transcribe = boto3.client("transcribe")

from mas_helper import OutputHelper
from mas_helper import MasExecutionError
from mas_helper import DataPlane

operator_name = 'transcribe'
output_object = OutputHelper(operator_name)


def lambda_handler(event, context):
        try:
            job_id = event["metadata"]["transcribe_job_id"]
            workflow_id = event["metadata"]["workflow_id"]
            asset_id = event["metadata"]["asset_id"]
        except KeyError as e:
            output_object.update_status("Error")
            output_object.update_metadata(transcribe_error="Missing a required metadata key {e}".format(e=e))
            raise MasExecutionError(output_object.return_output_object())

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
                output_object.update_metadata(transcribe_job_id=job_id, asset_id=asset_id, workflow_id=workflow_id)
                return output_object.return_output_object()
            elif response["TranscriptionJob"]["TranscriptionJobStatus"] == "FAILED":
                output_object.update_status("Error")
                output_object.update_metadata(transcribe_job_id=job_id,
                                              transcribe_error=str(response["TranscriptionJob"]["FailureReason"]))
                raise MasExecutionError(output_object.return_output_object())
            elif response["TranscriptionJob"]["TranscriptionJobStatus"] == "COMPLETED":
                transcribe_uri = response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                http = urllib3.PoolManager()
                transcription = http.request('GET', transcribe_uri)
                transcription_data = transcription.data.decode("utf-8")

                print(transcription_data)

                # TODO: Do we want to fail the operator if we cannot upload metadata or persist media?

                dataplane = DataPlane(asset_id, workflow_id)

                # Upload transcribe metadata for the asset
                transcription_json = json.loads(transcription_data)
                metadata_upload = dataplane.upload_metadata(operator_name, transcription_json['results'])
                if metadata_upload["status"] == "success":
                    print("Uploaded metadata for asset: {asset}".format(asset=asset_id))
                elif metadata_upload["status"] == "failed":
                    output_object.update_status("Error")
                    output_object.update_metadata(
                        transcribe_error="Unable to upload metadata for asset: {asset}".format(asset=asset_id),
                        transcribe_job_id=job_id)
                    raise MasExecutionError(output_object.return_output_object())
                else:
                    output_object.update_status("Error")
                    output_object.update_metadata(
                        transcribe_error="Unable to upload metadata for asset: {asset}".format(asset=asset_id),
                        transcribe_job_id=job_id)
                    raise MasExecutionError(output_object.return_output_object())

                # Persist raw transcription text in a file
                transcription = transcription_json["results"]["transcripts"][0]["transcript"]
                persist_media = dataplane.persist_media(data=transcription, file_name='{asset}-transcription.txt'.format(asset=asset_id))
                if persist_media["status"] == "failed":
                    output_object.update_status("Error")
                    output_object.update_metadata(
                        transcribe_error="Unable to persist media for asset: {asset}".format(asset=asset_id),
                        transcribe_job_id=job_id)
                    raise MasExecutionError(output_object.return_output_object())
                else:
                    s3bucket = persist_media['s3bucket']
                    s3key = persist_media['s3key']

                output_object.update_media(media_type='text', s3bucket=s3bucket, s3key=s3key)
                output_object.update_metadata(transcribe_job_id=job_id)
                output_object.update_status("Complete")
                return output_object.return_output_object()
            else:
                output_object.update_status("Error")
                output_object.update_metadata(transcribe_error="Unable to determine status")
                raise MasExecutionError(output_object.return_output_object())
