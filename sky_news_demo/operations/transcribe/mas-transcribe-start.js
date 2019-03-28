var AWS = require("aws-sdk");
var transcribe = new AWS.TranscribeService();

/**
 * Runs Amazon Transcribe to convert speech to text
 */
exports.handler = async (event) => {
    
    console.log('[INFO] got event: %j', event);
    
    try
    {
        var jobId = 'transcribe' + '-' + event.workflow_execution_id 

        var transcribeResponse = await transcribeAudio(event, jobId);

        if (transcribeResponse == 'Executing')
        {
            let output = {"name": "transcribe", "status": "Executing", "metadata": {"transcribeJobId": jobId, "bucket": event.input.media.audio.s3bucket} };
            return output
        }
        if (transcribeResponse == 'Error')
        {
            let output = {"name": "transcribe", "status": "Error", "metadata": {"transcribeJobId": jobId, "bucket": event.input.media.audio.s3bucket} };
            return output
        }
        if (transcribeResponse == 'Complete')
        {
            // Should never get here
            let output = {"name": "transcribe", "status": "Complete", "message": "We got complete when we iniated a job, likely a duplicate", "metadata": {"transcribeJobId": event.configuration.transcribe.transcribeJobId, "bucket": event.input.audio.bucket} };
            return output
        }

    }
    catch (error)
    {
        console.log('[ERROR] failed to start transcribe job', error);
        throw error;
    }
};

/**
 * Transcribes audio or video in the input
 */
async function transcribeAudio(event, name)
{
	try
	{   
	    const validTypes = ["mp3", "mp4", "wav", "flac"];
		
        if (event.input.media.audio)
        {
			var bucket = event.input.media.audio.s3bucket;
			var key = event.input.media.audio.s3key;
			var fileType = key.split('.')[1];
		}
		// Need to figure out if we want to allow this
        else if (event.input.media.video)
        {
            var bucket = event.input.media.video.s3bucket;
			var key = event.input.media.video.s3key;
			var fileType = key.split('.')[1];
        }
        else
        {
            throw new Error('[Error], no valid inputs');
        }
        
        console.log(fileType);

        if (!(validTypes.includes(fileType)))
        {
			throw new Error('[Error], no valid input file types. Only allowed types: %j', validTypes);
		}
        
		var transcribeParams = {
		  	LanguageCode: event.configuration.transcribe.transcribeLanguage,
			Media: 
			{
    			MediaFileUri: 'https://s3.' + process.env.AWS_REGION + '.amazonaws.com/' +
    			    bucket + '/' + key
  			},
  			MediaFormat: fileType,
			
			// Need to look into possibly updating this to random generation as to not rely on this input  
			TranscriptionJobName: name
		};
		
		if (event.configuration.transcribe.vocabularyName)
		{
		    transcribeParams.Settings.VocabularyName = event.transcribe.configuration.vocabularyName;
		}

		console.log("[INFO] about to launch Transcribe job with params: %j", 
			transcribeParams);

		var transcribeResult = await transcribe.startTranscriptionJob(transcribeParams).promise();

		console.log("[INFO] got startTranscriptionJob() response: %j", 
			transcribeResult);

        if (transcribeResult.TranscriptionJob.TranscriptionJobStatus == 'IN_PROGRESS')
        {
            return 'Executing'
        }
        if (transcribeResult.TranscriptionJob.TranscriptionJobStatus == 'FAILED')
        {
            return 'Error'
        }
        if (transcribeResult.TranscriptionJob.TranscriptionJobStatus == 'COMPLETED')
        {
            console.log('We should not be here, yet here we are, something is probably wrong', transcribeResult)
            return 'Complete'
        }

	}
	catch (error)
	{
		console.log("[ERROR] failed to launch Transcribe job", error);
		throw error;
	}
}
