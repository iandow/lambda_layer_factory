import os
import boto3

from mas_helper import OutputHelper
from mas_helper import MasExecutionError

region = os.environ["AWS_REGION"]

mediaconvert = boto3.client("mediaconvert", region_name=region)

operator_name = "mediaconvert"
output_object = OutputHelper(operator_name)


def lambda_handler(event, context):
    print("We got the following event:\n", event)
    try:
        job_id = event["metadata"]["mediaconvert_job_id"]
        workflow_id = event["metadata"]["workflow_id"]
        input_file = event["metadata"]["mediaconvert_input_file"]
    except KeyError as e:
        output_object.update_status("Error")
        output_object.update_metadata(mediaconvert_error="Missing a required metadata key {e}".format(e=e))
        raise MasExecutionError(output_object.return_output_object())

    try:
        asset_id = event["metadata"]["asset_id"]
    except KeyError as e:
        print("No asset_id in this workflow")
        asset_id = ''

    try:
        response = mediaconvert.describe_endpoints()
    except Exception as e:
        print("Exception:\n", e)
        output_object.update_status("Error")
        output_object.update_metadata(mediaconvert_error=str(e))
        raise MasExecutionError(output_object.return_output_object())
    else:
        mediaconvert_endpoint = response["Endpoints"][0]["Url"]
        customer_mediaconvert = boto3.client("mediaconvert", region_name=region, endpoint_url=mediaconvert_endpoint)

    try:
        response = customer_mediaconvert.get_job(Id=job_id)
    except Exception as e:
        print("Exception:\n", e)
        output_object.update_status("Error")
        output_object.update_metadata(mediaconvert_error=e, mediaconvert_job_id=job_id)
        raise MasExecutionError(output_object.return_output_object())
    else:
        if response["Job"]["Status"] == 'IN_PROGRESS' or response["Job"]["Status"] == 'PROGRESSING':
            output_object.update_status("Executing")
            output_object.update_metadata(mediaconvert_job_id=job_id,
                                          mediaconvert_input_file=input_file,
                                          asset_id=asset_id, workflow_id=workflow_id)
            return output_object.return_output_object()
        elif response["Job"]["Status"] == 'COMPLETE':
            output_uri = response["Job"]["Settings"]["OutputGroups"][0]["OutputGroupSettings"]["FileGroupSettings"][
                "Destination"]

            extension = response["Job"]["Settings"]["OutputGroups"][0]["Outputs"][0]["Extension"]
            modifier = response["Job"]["Settings"]["OutputGroups"][0]["Outputs"][0]["NameModifier"]

            bucket = output_uri.split("/")[2]
            folder = "/".join(output_uri.split("/")[3:-1])

            file_name = event["metadata"]["mediaconvert_input_file"].split("/")[-1].split(".")[0]

            key = folder + "/" + file_name + modifier + "." + extension

            output_object.update_media("audio", bucket, key)
            output_object.update_metadata(mediaconvert_job_id=job_id)
            output_object.update_status("Complete")

            return output_object.return_output_object()
        else:
            output_object.update_status("Error")
            output_object.update_metadata(
                mediaconvert_error="Unhandled exception, unable to get status from mediaconvert: {response}".format(
                    response=response),
                mediaconvert_job_id=job_id)
            raise MasExecutionError(output_object.return_output_object())

