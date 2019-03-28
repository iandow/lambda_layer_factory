var AWS = require("aws-sdk");

/**
 * Get status of an Amazon Media Convert job
 */

exports.handler = async (event) => {
    
    console.log('[INFO] got event: %j', event);
    
    try
    {
        var endpointParams = await getMediaConvertEndpoint();
        var mediaConvertOutput = await getMediaConvertStatus(event, endpointParams);
        console.log(mediaConvertOutput);

        if (mediaConvertOutput == 'Executing')
        {
            console.log(event);
            return event;
        }
        if (mediaConvertOutput == 'Error')
        {
            let output = {'name': 'mediaconvert', 'status': 'Error', 'metadata': {'job_id': event.metadata.job_id, 'input_key': event.metadata.input_key} };
            return output;
        }
        else
        {
            let output = {'name': 'mediaconvert', 'status': 'Complete', 'media': {'audio': {'s3bucket': mediaConvertOutput.s3bucket, 's3key': mediaConvertOutput.s3key}}, 'metadata': {'job_id': event.metadata.job_id, 'input_key': event.metadata.input_key} };
            return output;
        }

    }
    catch (error)
    {
        console.log('[ERROR] failed to get status of MediaConvert job', error);
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

        var endpoints = await mediaconvert.describeEndpoints().promise();
        var params = {
            "endpoint": endpoints.Endpoints[0].Url,
            "region": process.env.AWS_REGION
             };
        console.log(params);
        return params;
        }
        catch(error)
        {
            console.log("[ERROR] failed to get MediaConvert Endpoint", error);
		    throw error;
        }
}

async function getMediaConvertStatus(event, endpointParams)
{
    console.log(event);
    try
    {

       // Get setup new mediaconvert object with params from getMediaConvertEndpoint

        let mediaconvert = new AWS.MediaConvert({
            endpoint: endpointParams.endpoint,
            region: endpointParams.region
          });

       var id = event.metadata.job_id;

       var params = {
            Id: id
          };

       var response = await mediaconvert.getJob(params).promise();

       console.log(response);

       if (response.Job.Status == 'IN_PROGRESS' || response.Job.Status == 'PROGRESSING')
       {
          return 'Executing';
       }

       if (response.Job.Status == 'COMPLETE')
       {
          var uri = response.Job.Settings.OutputGroups[0].OutputGroupSettings.FileGroupSettings.Destination;

          console.log(uri);
          console.log(response.Job.Settings.OutputGroups[0].OutputGroupSettings.FileGroupSettings);
          console.log(response.Job.Settings.OutputGroups[0].OutputGroupSettings);
          console.log(response.Job.Settings.OutputGroups[0]);
          console.log(response.Job.Settings.OutputGroups);

          // Need to clean this up and find a better way to get the output key

          var split_uri = uri.split("/");
          var bucket = split_uri[2];
          var folder = split_uri[3];

          var input_file = event.metadata.input_key;
          var input_file_split = input_file.split("/");
          var file_name = input_file_split[1];
          var file_name_split = file_name.split(".");
          var name = file_name_split[0];

          var extension = response.Job.Settings.OutputGroups[0].Outputs[0].Extension;
          var modifier = response.Job.Settings.OutputGroups[0].Outputs[0].NameModifier;


          var key = folder + "/" + name + modifier + "." + extension;

          return {'s3bucket': bucket, 's3key': key};
          }
       if (response.Job.Status == 'ERROR')
       {
          return 'Error';
       }

    }
    catch(error)
    {
        console.log("[ERROR] failed to get status of MediaConvert job", error);
		throw error;
    }
}