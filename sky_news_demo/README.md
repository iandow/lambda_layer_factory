# How to deploy this stack:

* Zip each lambda into a zip file (zip $zipfilename $lambda_function_code). I'd recommend naming them as they're named in their corresponding cloudformation template. 
* Next create an S3 bucket and dump all the zipped functions in the root
* Now go to the cloudformation console and launch the datastore template, this will create a S3 bucket that all the functions will use as a 'working temp space'
* Grab the physical id of the datastore bucket (resources tab in cloudformation) and form it into an arn string like this: arn:aws:s3:::{replace_with_your_id}/* , keep this handy somewhere
* Okay, so now you have everything you need to deploy each operator. Launch each template passing in the sourcebucket (bucket you initally created manually with zips) and the datastore bucket (string you saved). If you named the zip files according to their parameter value as mentioned in beginning, each operator zip location should be filled out by default. If not, replace it with what you named the zip file.
* After all the operators are finished deploying, create a folder named video at the root of the datastore bucket
* That folder will serve as your upload point for any video you want to translate
* Update your preprocess request json with the correct bucket name and key
* Paste this json in the stepfunctions execution window for the preprocess stepfunction
* Rinse and repeat this process for the remaining stepfunctions, making sure to fill out all required params in the request

# Special considerations:

* Transcribe requires a full language code, e.g. 'en-US' whereas Translate only requires partial, e.g. 'en'
* Transcribe also requires a unique job id. Currently we are passing in that param from the workflowexecutionid field. This value needs to be changed each time you run to ensure uniqueness. 


