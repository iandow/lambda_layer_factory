import boto3

polly = boto3.client('polly')
s3 = boto3.client('s3')


def lambda_handler(event, context):

    print("We got this event:\n", event)

    bucket = event["input"]["media"]["text"]["s3bucket"]
    key = event["input"]["media"]["text"]["s3key"]

    s3_response = s3.get_object(Bucket=bucket, Key=key)
    translation = s3_response["Body"].read().decode("utf-8")

    polly_response = polly.start_speech_synthesis_task(
        OutputFormat='mp3',
        OutputS3BucketName=bucket,
        OutputS3KeyPrefix='audio/translation.mp3',
        Text=translation,
        TextType='text',
        VoiceId='Joey'
    )

    polly_job_id = polly_response['SynthesisTask']['TaskId']

    output = {"name": "polly", "status": "Executing", "metadata": {"polly_job_id": polly_job_id, "bucket": bucket } }

    print(output)

    return output


