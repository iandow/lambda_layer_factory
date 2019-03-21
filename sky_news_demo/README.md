# How to deploy this stack:

* Run the build-zips.sh (may need a chmod +x) script which will 1) Build lambda zips, 2) create an S3 sourcebucket, 3) Upload packages to that bucket. Keep note of the bucket name. 
* Now go to the cloudformation console and launch the datastore template, this will create a S3 bucket that all the functions will use as a 'working temp space'
* Grab the physical id of the datastore bucket (resources tab in cloudformation) and form it into an arn string like this: arn:aws:s3:::{replace_with_your_id}/* , keep this handy somewhere
* Okay, so now you have everything you need to deploy each operator. Launch each template passing in the sourcebucket (bucket our script created) and the datastore bucket (string you saved). The default values for the operator packages should be left unchanged (unless you deployed this manually or adjusted the build script)
* After all the operators are finished deploying, create a folder named video at the root of the datastore bucket
* That folder will serve as your upload point for any video you want to translate
* Update your preprocess request json with the correct bucket name and key
* Paste this json in the stepfunctions execution window for the preprocess stepfunction
* Rinse and repeat this process for the remaining stepfunctions, making sure to fill out all required params in the request

# Special considerations:

* Transcribe requires a full language code, e.g. 'en-US' whereas Translate only requires partial, e.g. 'en'
* Transcribe also requires you to provide a unique job_id. Make sure you change this in the request each time you run the transcribe stepfunction. 


