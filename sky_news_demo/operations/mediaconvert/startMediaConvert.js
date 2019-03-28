var AWS = require("aws-sdk");

/**
 * Starts an Amazon Media Convert Job
 */

exports.handler = async (event) => {

    console.log('[INFO] got event: %j', event);

    try
    {

       var endpointParams = await getMediaConvertEndpoint();
       var mediaconvertResponse = await startMediaConvert(event, endpointParams);

       console.log('Response', mediaconvertResponse)

       var output = {"name": "mediaconvert", "status": "Executing", "metadata": {"job_id": mediaconvertResponse.job_id, "input_key": event.input.media.video.s3key } };
       console.log(output)
       return output

    }
    catch (error)
    {
        console.log('[ERROR] failed to start MediaConvert job', error);
        throw error;
    }
};


async function getMediaConvertEndpoint() {

         // Instantiate mediaconvert
        try
        {
        let mediaconvert = new AWS.MediaConvert({
            region: process.env.AWS_REGION
          });

        // Get mediaconvert endpoint

        var endpoints = await mediaconvert.describeEndpoints().promise()
        var params = {
            "endpoint": endpoints.Endpoints[0].Url,
            "region": process.env.AWS_REGION
             }
        console.log(params)
        return params
        }
        catch(error)
        {
            console.log("[ERROR] failed to get MediaConvert Endpoint", error);
		    throw error;
        }
}



async function startMediaConvert(event, params)
{
    console.log(event)
    try
    {
        let destination = "s3://" + event.input.media.video.s3bucket + "/" + "audio" + "/";
        let fileInput = "s3://" + event.input.media.video.s3bucket + "/" + event.input.media.video.s3key;

        var MediaConvertParams = {
            "UserMetadata": {
              "SolutionID": process.env.SOLUTIONID
            },
            "Role": process.env.mediaconvertRole,
            "Settings": {
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
                "FileInput": fileInput
              }]
            }
        };

        // Get setup new mediaconvert object with params from getMediaConvertEndpoint

        let mediaconvert = new AWS.MediaConvert({
            endpoint: params.endpoint,
            region: params.region
          });


        // Start mediaconvert job

        console.log('We are starting mediaconvert')
        var response = await mediaconvert.createJob(MediaConvertParams).promise()
        console.log('Response from mediaconvert', response)

        return {"job_id": response.Job.Id}

    }
    catch(error)
    {
        console.log("[ERROR] failed to launch MediaConvert job", error);
		throw error;
    }
}