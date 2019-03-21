import boto3

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    print("We got this event:\n", event)

    bucket = event["input"]["media"]["audio"]["s3bucket"]
    key = 'metadata/transcription.txt'

    transcription = event["output"]["media"]["text"]["transcript"]
    encoded_transcription = transcription.encode("utf-8")

    s3_client.put_object(Bucket=bucket, Key=key, Body=encoded_transcription)

    event["output"]["media"]["text"]["s3bucket"] = bucket
    event["output"]["media"]["text"]["s3key"] = key

    print(event)

    return event


