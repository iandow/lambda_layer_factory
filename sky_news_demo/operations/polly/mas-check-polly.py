import boto3

polly = boto3.client('polly')
s3 = boto3.client('s3')

def lambda_handler(event, context):

    print("We got this event:\n", event)

    task_id = event['configuration']['polly']['pollyJobId']

    # Add error handling

    polly_response = polly.get_speech_synthesis_task(
        TaskId=task_id
    )

    polly_status = polly_response['SynthesisTask']['TaskStatus']

    print('The status from polly is:\n', polly_status)

    if polly_status == 'inProgress':
        event['status'] = 'inProgress'
        print(event)
        return event
    if polly_status == 'scheduled':
        event['status'] = 'inProgress'
        print(event)
        return event
    if polly_status == 'failed':
        event['status'] = 'Error'
        print(event)
        return event
    if polly_status == 'completed':
        event['status'] = 'Complete'
        uri = polly_response['SynthesisTask']['OutputUri']

        file = uri.split("/")[5]
        folder = uri.split("/")[4]
        bucket = uri.split("/")[3]

        key = folder + "/" + file

        output = {"media": {"audio": {"s3bucket": bucket, "s3key": key}}}

        event['output'] = output

        return event

    # Add else statement here to handle any weirdness
