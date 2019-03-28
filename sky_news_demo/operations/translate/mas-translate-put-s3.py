import boto3

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    print("We got this event:\n", event)

    bucket = event["metadata"]["bucket"]
    key = 'metadata/translation.txt'

    translation = event["metadata"]["translation"]
    encoded_transcription = translation.encode("utf-8")

    s3_client.put_object(Bucket=bucket, Key=key, Body=encoded_transcription)

    output = {"name": "translate", "status": "Complete", "media": {"text": {"s3bucket": bucket, "s3key": key} }}

    print(output)

    return output
