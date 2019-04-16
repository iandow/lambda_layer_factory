import os
import boto3
# TODO: Figure out how to build this module properly
from awsmie import OutputHelper
from awsmie import MasExecutionError

region = os.environ['AWS_REGION']
mediaconvert_role = os.environ['mediaconvertRole']


mediaconvert = boto3.client("mediaconvert", region_name=region)

operator_name = 'mediaconvert'
output_object = OutputHelper(operator_name)

def lambda_handler(event, context):
    print("We got the following event:\n", event)
    try:
        workflow_id = str(event["workflow_execution_id"])
        bucket = event["input"]["media"]["video"]["s3bucket"]
        key = event["input"]["media"]["video"]["s3key"]
    except KeyError as e:
        output_object.update_status("Error")
        output_object.update_metadata(mediaconvert_error="Missing a required metadata key {e}".format(e=e))
        raise MasExecutionError(output_object.return_output_object())

    # Adding in exception block for now since we aren't guaranteed an asset id will be present, should remove later
    try:
        asset_id = event['asset_id']
    except KeyError as e:
        print("No asset id passed in with this workflow", e)
        asset_id = ''

    file_input = "s3://" + bucket + "/" + key
    destination = "s3://" + bucket + "/" + 'private/media/' + asset_id + "/" + "derived" + "/" + workflow_id + "/"

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
        response = customer_mediaconvert.create_job(
            Role=mediaconvert_role,
            Settings={
              "OutputGroups": [{
                "Name": "File Group",
                "Outputs": [{
                  "ContainerSettings": {
                    "Container": "MP4",
                    "Mp4Settings": {
                      "CslgAtom": "INCLUDE",
                      "FreeSpaceBox": "EXCLUDE",
                      "MoovPlacement": "PROGRESSIVE_DOWNLOAD"
                    }
                  },
                  "AudioDescriptions": [{
                    "AudioTypeControl": "FOLLOW_INPUT",
                    "AudioSourceName": "Audio Selector 1",
                    "CodecSettings": {
                      "Codec": "AAC",
                      "AacSettings": {
                        "AudioDescriptionBroadcasterMix": "NORMAL",
                        "Bitrate": 96000,
                        "RateControlMode": "CBR",
                        "CodecProfile": "LC",
                        "CodingMode": "CODING_MODE_2_0",
                        "RawFormat": "NONE",
                        "SampleRate": 48000,
                        "Specification": "MPEG4"
                      }
                    },
                    "LanguageCodeControl": "FOLLOW_INPUT"
                  }],
                  "Extension": "mp4",
                  "NameModifier": "_audio"
                }],
                "OutputGroupSettings": {
                  "Type": "FILE_GROUP_SETTINGS",
                  "FileGroupSettings": {
                    "Destination": destination
                  }
                }
              }],
              "AdAvailOffset": 0,
              "Inputs": [{
                "AudioSelectors": {
                  "Audio Selector 1": {
                    "Offset": 0,
                    "DefaultSelection": "DEFAULT",
                    "ProgramSelection": 1
                  }
                },
                "VideoSelector": {
                  "ColorSpace": "FOLLOW"
                },
                "FilterEnable": "AUTO",
                "PsiControl": "USE_PSI",
                "FilterStrength": 0,
                "DeblockFilter": "DISABLED",
                "DenoiseFilter": "DISABLED",
                "TimecodeSource": "EMBEDDED",
                "FileInput": file_input
              }]
            }
        )
    # TODO: Add support for boto client error handling
    except Exception as e:
        print("Exception:\n", e)
        output_object.update_status("Error")
        output_object.update_metadata(mediaconvert_error=str(e))
        raise MasExecutionError(output_object.return_output_object())
    else:
        job_id = response['Job']['Id']
        output_object.update_status("Executing")
        output_object.update_metadata(mediaconvert_job_id=job_id, mediaconvert_input_file=key, asset_id=asset_id, workflow_id=workflow_id)
        return output_object.return_output_object()

