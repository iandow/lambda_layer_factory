import boto3

from mas_helper import OutputHelper
from mas_helper import MasExecutionError
from mas_helper import DataPlane

translate_client = boto3.client('translate')
s3 = boto3.client('s3')

operator_name = "translate"
output_object = OutputHelper(operator_name)


def lambda_handler(event, context):
        print("We got the following event:\n", event)

        try:
            bucket = event["input"]["media"]["text"]["s3bucket"]
            key = event["input"]["media"]["text"]["s3key"]
        except KeyError as e:
            output_object.update_status("Error")
            output_object.update_metadata(translate_error="No valid inputs {e}".format(e=e))
            raise MasExecutionError(output_object.return_output_object())

        try:
            workflow_id = event["workflow_execution_id"]
        except KeyError as e:
            output_object.update_status("Error")
            output_object.update_metadata(translate_error="Missing a required metadata key {e}".format(e=e))
            raise MasExecutionError(output_object.return_output_object())

        try:
            asset_id = event["asset_id"]
        except KeyError:
            print('No asset id for this workflow')
            asset_id = ''

        try:
            source_lang = event["configuration"]["translate"]["SourceLanguageCode"]
            target_lang = event["configuration"]["translate"]["TargetLanguageCode"]
        except KeyError:
            output_object.update_status("Error")
            output_object.update_metadata(translate_error="Language codes are not defined")
            raise MasExecutionError(output_object.return_output_object())

        try:
            s3_response = s3.get_object(Bucket=bucket, Key=key)
            transcript = s3_response["Body"].read().decode("utf-8")
            print(transcript)
        except Exception as e:
            output_object.update_status("Error")
            output_object.update_metadata(translate_error="Unable to read transcription from S3: {e}".format(e=str(e)))
            raise MasExecutionError(output_object.return_output_object())

        try:
            translation = translate_client.translate_text(
                Text=transcript,
                SourceLanguageCode=source_lang,
                TargetLanguageCode=target_lang
            )
        except Exception as e:
            output_object.update_status("Error")
            output_object.update_metadata(translate_error="Unable to get response from translate: {e}".format(e=str(e)))
            raise MasExecutionError(output_object.return_output_object())
        else:
            dataplane = DataPlane(asset_id, workflow_id)

            # Upload translate metadata for asset in dataplane
            metadata_upload = dataplane.upload_metadata(operator_name, translation)
            if metadata_upload["status"] == "success":
                print("Uploaded metadata for asset: {asset}".format(asset=asset_id))
            elif metadata_upload["status"] == "failed":
                output_object.update_status("Error")
                output_object.update_metadata(
                    translate_error="Unable to upload metadata for asset: {asset}".format(asset=asset_id))
                raise MasExecutionError(output_object.return_output_object())
            else:
                output_object.update_status("Error")
                output_object.update_metadata(
                    translate_error="Unable to upload metadata for asset: {asset}".format(asset=asset_id))
                raise MasExecutionError(output_object.return_output_object())


            # Persist translation to a text file in s3

            translated_transcript = translation["TranslatedText"]
            persist_media = dataplane.persist_media(data=translated_transcript,
                                                    file_name='{asset}-translation.txt'.format(asset=asset_id))
            if persist_media["status"] == "failed":
                output_object.update_status("Error")
                output_object.update_metadata(
                    translate_error="Unable to persist media for asset: {asset}".format(asset=asset_id))
                raise MasExecutionError(output_object.return_output_object())
            else:
                s3bucket = persist_media['s3bucket']
                s3key = persist_media['s3key']

                output_object.update_media(media_type="text", s3bucket=s3bucket, s3key=s3key)
                output_object.update_metadata(translation=translated_transcript)
                output_object.update_status("Complete")
                return output_object.return_output_object()

