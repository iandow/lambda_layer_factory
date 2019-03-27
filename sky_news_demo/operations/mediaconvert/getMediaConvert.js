var AWS = require("aws-sdk");

/**
 * Get status of an Amazon Media Convert job
 */

exports.handler = async (event) => {
    
    console.log('[INFO] got event: %j', event);
    
    try
    {
        var mediaConvertOutput = await getMediaConvertStatus(event);
        console.log('[INFO] Response from mediaconvert', mediaConvertOutput);

        return output;
    }
    catch (error)
    {
        console.log('[ERROR] failed to get status of MediaConvert job', error);
        throw error;
    }
};

async function getMediaConvertStatus(event)
{
    console.log(event)
    try
    {
        var mediaconvert = new AWS.MediaConvert({
            region: process.env.AWS_REGION
          });
        await mediaconvert.describeEndpoints().promise()
        .then(data => {

          // Create a new MediaConvert object with an endpoint.
          mediaconvert = new AWS.MediaConvert({
            endpoint: data.Endpoints[0].Url,
            region: process.env.AWS_REGION
          });

          let params = {
            Id: event.configuration.mediaconvert.job_id
          };


           return mediaconvert.getJob(params).promise();

        })
        .then(data => {
          console.log(data)
          event.status = data.Job.Status;

          if (data.Job.Status == 'Complete')
          {


              var uri = data.Job.Settings.OutputGroups[0].OutputGroupSettings.FileGroupSettings.Destination;

              console.log(uri);
              console.log(data.Job.Settings.OutputGroups[0].OutputGroupSettings.FileGroupSettings);
              console.log(data.Job.Settings.OutputGroups[0].OutputGroupSettings);
              console.log(data.Job.Settings.OutputGroups[0]);
              console.log(data.Job.Settings.OutputGroups);

              // Need to clean this up and find a better way to get the output key

              var split_uri = uri.split("/");
              var bucket = split_uri[2];
              var folder = split_uri[3];

              var input_file = event.input.media.video.s3key;
              var input_file_split = input_file.split("/");
              var file_name = input_file_split[1];
              var file_name_split = file_name.split(".");
              var name = file_name_split[0];

              var extension = data.Job.Settings.OutputGroups[0].Outputs[0].Extension;
              var modifier = data.Job.Settings.OutputGroups[0].Outputs[0].NameModifier;


              var key = folder + "/" + name + modifier + "." + extension;

              var output = {
                             "name": "mediaconvert",
                             "media": {
                                 "audio":
                                   {
                                     "s3bucket": bucket,
                                     "s3key": key
                                    }
                               },
                               "status": "Complete",
                               "message": "No errors"
                            };
          }

        })
    }
    catch(error)
    {
        console.log("[ERROR] failed to get status of MediaConvert job", error);
		throw error;
    }
}