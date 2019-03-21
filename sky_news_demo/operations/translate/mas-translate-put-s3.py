import boto3

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    print("We got this event:\n", event)

    bucket = event["input"]["media"]["text"]["s3bucket"]
    key = 'metadata/translation.txt'

    translation = event["output"]["media"]["text"]["translation"]
    encoded_transcription = translation.encode("utf-8")

    s3_client.put_object(Bucket=bucket, Key=key, Body=encoded_transcription)

    event["output"]["media"]["text"]["s3bucket"] = bucket
    event["output"]["media"]["text"]["s3key"] = key
    event["status"] = "COMPLETE"

    print(event)

    return event