import boto3

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    print("We got this event:\n", event)

    bucket = event["metadata"]["bucket"]
    key = 'metadata/transcription.txt'

    transcription = event["metadata"]["transcription"]
    encoded_transcription = transcription.encode("utf-8")

    s3_client.put_object(Bucket=bucket, Key=key, Body=encoded_transcription)

    output = {"name": "transcribe", "status": "Complete", "media": {"text": {"s3bucket": bucket, "s3key": key} }, "metadata": {"transcribeJobId": event["metadata"]["transcribeJobId"]} }

    print(output)

    return output
