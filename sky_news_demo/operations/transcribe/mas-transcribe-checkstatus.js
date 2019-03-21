var AWS = require("aws-sdk");
var transcribe = new AWS.TranscribeService();

/**
 * Checks the results of an Amazon Transcribe job
 */
exports.handler = async (event) => {
    
    console.log('[INFO] processing event: %j', event);
    
    try
    {
        event.status = await checkResults(event, 0);
        return event;
    }
    catch (error)
    {
        console.log('[ERROR] failed to start transcribe job', error);
        throw error;
    }
};

/**
 * Pause for the requested millis
 */
async function pause(duration = 0) 
{
    return new Promise(resolve =>
      setTimeout(() => resolve(), duration));
}

/**
 * Checks the results of a Transcribe job backing off for max count retries
 */
async function checkResults(event, count)
{
    const sleepMillis = 1000;
    const maxCount = 30;
    
    if (count < maxCount)
    {
    	try
    	{
    		var transcribeParams = {
      			TranscriptionJobName: event.configuration.transcribe.transcribeJobId
    		};
    		
    		console.log("[INFO] about to launch check job status with params: %j", transcribeParams);
    
    		var transcribeResult = await transcribe.getTranscriptionJob(transcribeParams).promise();
    		
    		console.log("[INFO] got getTranscriptionJob() response: %j", transcribeResult);
    		
		    if (transcribeResult.TranscriptionJob.TranscriptionJobStatus === 'IN_PROGRESS')
		    {
		        return 'Executing';
		    }
		    else if (transcribeResult.TranscriptionJob.TranscriptionJobStatus === 'COMPLETED')
		    {
		        return 'Complete';
		    }
		    else if (transcribeResult.TranscriptionJob.TranscriptionJobStatus === 'FAILED')
		    {
		        return 'Error';
		    }

            throw new Error("Invalid Transcribe response: %j", transcribeResult);
    	}
    	catch (error)
    	{
    		console.log("[ERROR] failed to check Transcribe job status", error);
    		await pause(sleepMillis);
    		return checkResults(event, count++);
    	}
    }
    
    throw new Error('Maximum retries exceeded');
}
