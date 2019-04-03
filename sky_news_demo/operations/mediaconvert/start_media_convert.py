import os
import boto3
# TODO: Figure out how to build this module properly
from outputHelper import OutputHelper
from outputHelper import MasExecutionError

region = os.environ['AWS_REGION']
mediaconvert_role = os.environ['mediaconvertRole']

mediaconvert = boto3.client("mediaconvert", region_name=region)

operator_name = 'mediaconvert'
output_object = OutputHelper(operator_name)

def lambda_handler(event, context):
    print("We got the following event:\n", event)

    bucket = event["input"]["media"]["video"]["s3bucket"]
    key = event["input"]["media"]["video"]["s3key"]

    destination = "s3://" + bucket + "/" + "audio" + "/"
    file_input = "s3://" + bucket + "/" + key

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
        output_object.update_metadata(mediaconvert_job_id=job_id, mediaconvert_input_file=key)
        return output_object.return_output_object()

