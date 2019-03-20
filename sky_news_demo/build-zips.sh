#!/bin/bash

if [[ -d ./operations ]]; then

echo "Zipping files"

mkdir ./zips

# Mediaconvert

zip ./zips/startMediaConvert.zip ./operations/mediaconvert/startMediaConvert.js
zip ./zips/getMediaConvert.zip ./operations/mediaconvert/getMediaConvert.js


# Transcribe

zip ./zips/startTranscribe.zip ./operations/transcribe/mas-transcribe-start.js
zip ./zips/checkTranscribe.zip ./operations/transcribe/mas-transcribe-checkstatus.js
zip ./zips/putS3Transcribe.zip ./operations/transcribe/mas-transcribe-put-s3.py
zip ./zips/resultTranscribe.zip ./operations/transcribe/mas-transcribe-result.js

# Polly

zip ./zips/startPolly.zip ./operations/polly/mas-start-polly.py
zip ./zips/checkPolly.zip ./operations/polly/mas-check-polly.py


# Translate

zip ./zips/startTranslate.zip ./operations/translate/mas-translate.py
zip ./zips/putS3Translate.zip ./operations/translate/mas-translate-put-s3.py

elif [[ ! -d ./operations ]]; then

echo "This script needs to be run from the sky_news_demo directory"

exit 1

fi

if [[ -d ~/.aws ]]; then

echo "This script assumes your aws cli is setup correctly. Here is the config we have:"
cat ~/.aws/config
echo "Ensure this is the region you want to deploy too"
echo "Please verify you have the correct access keys in your credentials file and iam permissions to create an s3 bucket"

read -p "Is your AWS CLI Setup correctly? (y or yes to continue)"  confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1

bucket="skysourcecode`date +%s`"
echo "We are creating an s3 bucket named $bucket in your configured AWS account"

aws s3 mb s3://$bucket/

fi
echo "We are copying in your zipped up source into the newly created bucket"

for zip in ./zips/*
do
    echo $zip
    aws s3 cp $zip s3://$bucket
done

echo "Done! Proceed on to deploying the rest of the stack as described in the readme"

