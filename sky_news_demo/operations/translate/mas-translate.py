import boto3

from outputHelper import OutputHelper
from outputHelper import MasExecutionError

translate_client = boto3.client('translate')
s3 = boto3.client('s3')

operator_name = "translate"
output_object = OutputHelper(operator_name)


def lambda_handler(event, context):
        try:
            bucket = event["input"]["media"]["text"]["s3bucket"]
            key = event["input"]["media"]["text"]["s3key"]
        except KeyError:
            output_object.update_status("Error")
            output_object.update_metadata(translate_error="No valid inputs")
            raise MasExecutionError(output_object.return_output_object())

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
            translated_transcript = translation["TranslatedText"]
            output_object.update_metadata(translation=translated_transcript)
            output_object.update_status("Complete")
            return output_object.return_output_object()

