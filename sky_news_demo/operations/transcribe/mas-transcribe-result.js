var AWS = require("aws-sdk");
var transcribe = new AWS.TranscribeService();
const HTTPS = require('https');

/**
 * Load the results of a transcription from Transcribe
 */
exports.handler = async (event) => {
    
    console.log('[INFO] processing event: %j', event);
    
    try
    {
        var transcribeResult = await getResults(event, 0);
        
        var transcript = transcribeResult.results.transcripts[0].transcript;

        console.log(transcript)

        var output =  {
                    "name": "transcribe",
                    "status": "Complete",
                     "metadata": {
                        "transcribeJobId": event.metadata.transcribeJobId,
                        "bucket": event.metadata.bucket,
                        "transcription": transcript
                     }
             };

        return output;
    }
    catch (error)
    {
        console.log('[ERROR] failed to fetch results from Transcribe');
        throw error;
    }
};

/**
 * Sleeps for the requested millis
 */
async function pause(duration = 0) 
{
    return new Promise(resolve =>
      setTimeout(() => resolve(), duration));
}

/**
 * Loads Transcribe results from remote URL
 */
async function loadResultData(resultLocation)
{
    const promise = new Promise((resolve, reject) => {
      const buffers = [];

      const request = HTTPS.request(resultLocation, (response) => {
        response.on('data', chunk =>
            buffers.push(chunk));

            response.on('end', () => {
                if (response.statusCode >= 400) {
                    reject(new Error('Failed to load data from: ' + resultLocation));
                    return;
                }
                resolve(Buffer.concat(buffers).toString());
            });
        });

        request.on('error', e =>
            reject(e));

        request.end();
    });

    return promise;
}

/**
 * Loads results from Transcribe retrying failures
 */
async function getResults(event, count)
{
    const sleepMillis = 1000;
    const maxCount = 30;
    
    if (count < maxCount)
    {
        try
        {
    		var transcribeParams = {
      			TranscriptionJobName: event.metadata.transcribeJobId
    		};
    		
    		console.log("[INFO] about to load Transcribe parameters with params: %j", transcribeParams);
    
    		var transcribeResult = await transcribe.getTranscriptionJob(transcribeParams).promise();
    		
    		console.log("[INFO] got getTranscriptionJob() response: %j", transcribeResult);
    		
            if (transcribeResult.TranscriptionJob.TranscriptionJobStatus === 'COMPLETED')
            {
    		    var json = await loadResultData(transcribeResult.TranscriptionJob.Transcript.TranscriptFileUri);
    		    console.log('[INFO] got result from transcribe:\n%j', json);
                return JSON.parse(json);                

    		}
    		else
    		{
    		    throw new Error('Invalid response from Transcribe: %j', transcribeResult);
    		}
        }
        catch (error)
        {
    		console.log("[ERROR] failed to fetch Transcribe job results", error);
    		await pause(sleepMillis);
    		return getResults(event, count++);
        }
    }
    
    throw new Error('Maximum retry count exceeded');
}
