import json


def lambda_handler(event, context):
    error = event["outputs"]["Cause"]

    try:
        error_json = json.loads(error)
        error_message = error_json["errorMessage"]
    except ValueError:
        # Not an output object that can be converted to JSON, must be an unhandled error, returning it directly
        return error
    else:
        return error_message
