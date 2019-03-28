import boto3

polly = boto3.client('polly')
s3 = boto3.client('s3')

def lambda_handler(event, context):

    print("We got this event:\n", event)

    task_id = event['metadata']['polly_job_id']

    # Add error handling

    polly_response = polly.get_speech_synthesis_task(
        TaskId=task_id
    )

    polly_status = polly_response['SynthesisTask']['TaskStatus']

    print('The status from polly is:\n', polly_status)

    if polly_status == 'inProgress':
        output = {"name": "polly", "status": "Executing", "metadata": {"polly_job_id": task_id, "bucket": event["metadata"]["bucket"]} }
        return output
    if polly_status == 'scheduled':
        output = {"name": "polly", "status": "Executing", "metadata": {"polly_job_id": task_id, "bucket": event["metadata"]["bucket"] } }
        return output
    if polly_status == 'failed':
        output = {"name": "polly", "status": "Error", "metadata": {"polly_job_id": task_id, "bucket": event["metadata"]["bucket"] } }
        return output
    if polly_status == 'completed':
        uri = polly_response['SynthesisTask']['OutputUri']

        file = uri.split("/")[5]
        folder = uri.split("/")[4]
        bucket = uri.split("/")[3]

        key = folder + "/" + file

        output = {"name": "polly", "status": "Complete", "media": {"audio": {"s3bucket": bucket, "s3key": key}}, "metadata": {"polly_job_id": task_id} }

        return output

    # Add else statement here to handle any weirdness
