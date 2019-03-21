var AWS = require("aws-sdk");
var transcribe = new AWS.TranscribeService();

/**
 * Runs Amazon Transcribe to convert speech to text
 */
exports.handler = async (event) => {
    
    console.log('[INFO] got event: %j', event);
    
    try
    {
        await transcribeAudio(event); 
        event.status = 'Executing';
        return event;
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
async function transcribeAudio(event)
{
	try
	{
	    var media = null;
	    
	    const validTypes = ["mp3", "mp4", "wav", "flac"];
	    
        if (event.input.media.audio && validTypes.includes(event.input.media.audio.fileType))
        {
            media = event.input.media.audio;
        }
        else if (event.input.media.video && validTypes.includes(event.input.media.video.fileType))
        {
            media = event.input.media.video;
        }
        else
        {
            throw new Error('Invalid input, only supports audio or video with file type: %j', validTypes);
        }
        
		var transcribeParams = {
		  	LanguageCode: event.configuration.transcribe.transcribeLanguage,
			Media: 
			{
    			MediaFileUri: 'https://s3.' + process.env.AWS_REGION + '.amazonaws.com/' +
    			    media.s3bucket + '/' + media.s3key
  			},
  			MediaFormat: media.fileType,
  			TranscriptionJobName: event.configuration.transcribe.transcribeJobId
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
	}
	catch (error)
	{
		console.log("[ERROR] failed to launch Transcribe job", error);
		throw error;
	}
}
