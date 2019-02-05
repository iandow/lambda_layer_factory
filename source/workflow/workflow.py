import boto3

def lambda_handler(event, context):
    print(json.dumps(event))
    
    stateMachineArn = event["stateMachineArn"]
    
    return event