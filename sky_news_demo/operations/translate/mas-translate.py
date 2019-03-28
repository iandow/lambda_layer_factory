import boto3


translate_client = boto3.client('translate')
s3 = boto3.client('s3')


def lambda_handler(event, context):
    # move these to pull from event

    bucket = event["input"]["media"]["text"]["s3bucket"]
    key = event["input"]["media"]["text"]["s3key"]

    source_lang = event["configuration"]["translate"]["SourceLanguageCode"]
    target_lang = event["configuration"]["translate"]["TargetLanguageCode"]

    s3_response = s3.get_object(Bucket=bucket, Key=key)
    transcript = s3_response["Body"].read().decode("utf-8")

    print(transcript)

    # Need to add error handling

    translation = translate_client.translate_text(
        Text=transcript,
        SourceLanguageCode=source_lang,
        TargetLanguageCode=target_lang
    )

    translated_transcript = translation["TranslatedText"]

    output = {"name": "translate", "metadata": {"translation": translated_transcript, "bucket": bucket} }

    return output

