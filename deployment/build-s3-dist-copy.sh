#!/bin/bash

# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# This assumes all of the OS-level configuration has been completed and git repo has already been cloned

# This script should be run from the repo's deployment directory
# cd deployment
# ./build-s3-dist.sh source-bucket-base-name
# source-bucket-base-name should be the base name for the S3 bucket location where the template will source the Lambda code from.
# The template will append '-[region_name]' to this bucket name.
# For example: ./build-s3-dist.sh solutions
# The template will then expect the source code to be located in the solutions-[region_name] bucket

# Check to see if input has been provided:
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Please provide the base source bucket name,  version where the lambda code will eventually reside and the region of the deploy."
    echo "For example: ./build-s3-dist.sh solutions v1.0.0 us-east-1"
    exit 1
fi

bucket_basename=$1
version=$2
region=$3
bucket=$1-$3

echo "------------------------------------------------------------------------------"
echo "Build S3 Bucket"
echo "------------------------------------------------------------------------------"
# Build source S3 Bucket

# if [[ -d ~/.aws ]]; then

# echo "This script assumes your aws cli is setup correctly. Here is the config we have:"
# cat ~/.aws/config
# echo "Ensure this is the region you want to deploy too"
# echo "Please verify you have the correct access keys in your credentials file and iam permissions to create an s3 bucket"

# read -p "Is your AWS CLI Setup correctly? (y or yes to continue)"  confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1

# bucket="$1`date +%s`"
# echo "We are creating an s3 bucket named $bucket in your configured AWS account"

# aws s3 mb s3://$bucket/

# elif [[ ! -d ~/.aws ]]; then

# echo "This script requires the AWS CLI to be setup"

# exit 1

# fi



# Get reference for all important folders
template_dir="$PWD"
dist_dir="$template_dir/dist"
source_dir="$template_dir/../source"
sky_demo_dir="$template_dir/../sky_news_demo/"


echo "------------------------------------------------------------------------------"
echo "Rebuild distribution"
echo "------------------------------------------------------------------------------"
# Setting up directories
echo "rm -rf $dist_dir"
rm -rf "$dist_dir"
# Create new dist directory
echo "mkdir -p $dist_dir"
mkdir -p "$dist_dir"

echo "------------------------------------------------------------------------------"
echo "MAS 1.0 CloudFormation Templates"
echo "------------------------------------------------------------------------------"
# Copy deploy template to dist directory and update bucket name

: '''
echo "cp $template_dir/media-analysis-deploy.yaml $dist_dir/media-analysis-deploy.template"
cp "$template_dir/media-analysis-deploy.yaml" "$dist_dir/media-analysis-deploy.template"

echo "Updating code source bucket in template with '$1'"
replace="s/%%BUCKET_NAME%%/$1/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-deploy.template"
sed -i '' -e $replace "$dist_dir/media-analysis-deploy.template"

echo "Replacing solution version in template with '$2'"
replace="s/%%VERSION%%/$2/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-deploy.template"
sed -i '' -e $replace "$dist_dir/media-analysis-deploy.template"

# Copy api template to dist directory and update bucket name
echo "cp $template_dir/media-analysis-api-stack.yaml $dist_dir/media-analysis-api-stack.template"
cp "$template_dir/media-analysis-api-stack.yaml" "$dist_dir/media-analysis-api-stack.template"

# Copy storage template to dist directory and update bucket name
echo "cp $template_dir/media-analysis-storage-stack.yaml $dist_dir/media-analysis-storage-stack.template"
cp "$template_dir/media-analysis-storage-stack.yaml" "$dist_dir/media-analysis-storage-stack.template"

# Copy state machine template to dist directory
echo "cp $template_dir/media-analysis-state-machine-stack.yaml $dist_dir/media-analysis-state-machine-stack.template"
cp "$template_dir/media-analysis-state-machine-stack.yaml" "$dist_dir/media-analysis-state-machine-stack.template"

echo "Updating code source bucket in template with '$1'"
replace="s/%%BUCKET_NAME%%/$1/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-api-stack.template"
sed -i '' -e $replace "$dist_dir/media-analysis-api-stack.template"

echo "Replacing solution version in template with '$2'"
replace="s/%%VERSION%%/$2/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-api-stack.template"
sed -i '' -e $replace "$dist_dir/media-analysis-api-stack.template"

'''

echo "------------------------------------------------------------------------------"
echo "MAS 2.0 CloudFormation Templates"
echo "------------------------------------------------------------------------------"

# Instant Translate template
echo "Copying instant translate template to dist directory"
echo "cp $template_dir/sky_instant_translate.yaml $dist_dir/sky_instant_translate.template"
cp "$template_dir/sky_instant_translate.yaml" "$dist_dir/sky_instant_translate.template"

echo "Updating code source bucket in instant translate template with '$bucket'"
replace="s/%%BUCKET_NAME%%/$bucket/g"
echo "sed -i '' -e $replace $dist_dir/sky_instant_translate.template"
sed -i '' -e $replace "$dist_dir/sky_instant_translate.template"

echo "Replacing solution version in template with '$2'"
replace="s/%%VERSION%%/$2/g"
echo "sed -i '' -e $replace $dist_dir/sky_instant_translate.template"
sed -i '' -e $replace "$dist_dir/sky_instant_translate.template"

# Workflow template
echo "Copying workflow template to dist directory"
echo "cp $template_dir/media-analysis-workflow-stack.yaml $dist_dir/media-analysis-workflow-stack.template"
cp "$template_dir/media-analysis-workflow-stack.yaml" "$dist_dir/media-analysis-workflow-stack.template"

echo "Updating code source bucket in workflow template with '$bucket'"
replace="s/%%BUCKET_NAME%%/$bucket/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-workflow-stack.template"
sed -i '' -e $replace "$dist_dir/media-analysis-workflow-stack.template"

echo "Replacing solution version in template with '$2'"
replace="s/%%VERSION%%/$2/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-workflow-stack.template"
sed -i '' -e $replace "$dist_dir/media-analysis-workflow-stack.template"

# Operations template
echo "Copying operations template to dist directory"
echo "cp $template_dir/media-analysis-test-operations-stack.yaml $dist_dir/media-analysis-test-operations-stack.template"
cp "$template_dir/media-analysis-test-operations-stack.yaml" "$dist_dir/media-analysis-test-operations-stack.template"

echo "Updating code source bucket in operations template with '$bucket'"
replace="s/%%BUCKET_NAME%%/$bucket/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-test-operations-stack.template"
sed -i '' -e $replace "$dist_dir/media-analysis-test-operations-stack.template"

echo "Replacing solution version in template with '$2'"
replace="s/%%VERSION%%/$2/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-test-operations-stack.template"
sed -i '' -e $replace "$dist_dir/media-analysis-test-operations-stack.template"

# Copy state machine template to dist directory
echo "cp $template_dir/media-analysis-preprocess-state-machine-stack.yaml $dist_dir/media-analysis-preprocess-state-machine-stack.template"
cp "$template_dir/media-analysis-preprocess-state-machine-stack.yaml" "$dist_dir/media-analysis-preprocess-state-machine-stack.template"


echo "------------------------------------------------------------------------------"
echo "Mediaconvert  Operations"
echo "------------------------------------------------------------------------------"

echo "Building Stage completion function"
cd "$source_dir/operations/mediaconvert" || exit

[ -e dist ] && rm -r dist
mkdir -p dist

[ -e package ] && rm -r package
mkdir -p package

echo "create requirements for lambda"

#pipreqs . --force

# Make lambda package

pushd package
echo "create lambda package"

# Handle distutils install errors

touch ./setup.cfg

echo "[install]" > ./setup.cfg
echo "prefix= " >> ./setup.cfg

# Try and handle failure if pip version mismatch
if [ -x "$(command -v pip)" ]; then
  pip install -r ../requirements.txt --target .

elif [ -x "$(command -v pip3)" ]; then
  echo "pip not found, trying with pip3"
  pip3 install -r ../requirements.txt --target .

elif ! [ -x "$(command -v pip)" ] && ! [ -x "$(command -v pip3)" ]; then
 echo "No version of pip installed. This script requires pip. Cleaning up and exiting."
 exit 1
fi

if ! [ -d ../dist/start_media_convert.zip ]; then
  zip -r9 ../dist/start_media_convert.zip .

elif [ -d ../dist/start_media_convert.zip ]; then
  echo "Package already present"
fi

if ! [ -d ../dist/get_media_convert.zip ]; then
  zip -r9 ../dist/get_media_convert.zip .

elif [ -d ../dist/get_media_convert.zip ]; then
  echo "Package already present"
fi

popd

zip -g dist/start_media_convert.zip start_media_convert.py awsmie.py
zip -g dist/get_media_convert.zip get_media_convert.py awsmie.py

cp "./dist/start_media_convert.zip" "$dist_dir/start_media_convert.zip"
cp "./dist/get_media_convert.zip" "$dist_dir/get_media_convert.zip"

echo "------------------------------------------------------------------------------"
echo "Transcribe  Operations"
echo "------------------------------------------------------------------------------"

echo "Building Stage completion function"
cd "$source_dir/operations/transcribe" || exit

[ -e dist ] && rm -r dist
mkdir -p dist

[ -e package ] && rm -r package
mkdir -p package

echo "create requirements for lambda"

#pipreqs . --force

# Make lambda package

pushd package
echo "create lambda package"

# Handle distutils install errors

touch ./setup.cfg

echo "[install]" > ./setup.cfg
echo "prefix= " >> ./setup.cfg

# Try and handle failure if pip version mismatch
if [ -x "$(command -v pip)" ]; then
  pip install -r ../requirements.txt --target .

elif [ -x "$(command -v pip3)" ]; then
  echo "pip not found, trying with pip3"
  pip3 install -r ../requirements.txt --target .

elif ! [ -x "$(command -v pip)" ] && ! [ -x "$(command -v pip3)" ]; then
 echo "No version of pip installed. This script requires pip. Cleaning up and exiting."
 exit 1
fi

if ! [ -d ../dist/start_transcribe.zip ]; then
  zip -r9 ../dist/start_transcribe.zip .

elif [ -d ../dist/start_transcribe.zip ]; then
  echo "Package already present"
fi

if ! [ -d ../dist/get_transcribe.zip ]; then
  zip -r9 ../dist/get_transcribe.zip .

elif [ -d ../dist/get_transcribe.zip ]; then
  echo "Package already present"
fi

popd

zip -g dist/start_transcribe.zip start_transcribe.py awsmie.py
zip -g dist/get_transcribe.zip get_transcribe.py awsmie.py

cp "./dist/start_transcribe.zip" "$dist_dir/start_transcribe.zip"
cp "./dist/get_transcribe.zip" "$dist_dir/get_transcribe.zip"

echo "------------------------------------------------------------------------------"
echo "Translate  Operations"
echo "------------------------------------------------------------------------------"

echo "Building Stage completion function"
cd "$source_dir/operations/translate" || exit

[ -e dist ] && rm -r dist
mkdir -p dist

[ -e package ] && rm -r package
mkdir -p package

echo "create requirements for lambda"

#pipreqs . --force

# Make lambda package

pushd package
echo "create lambda package"

# Handle distutils install errors

touch ./setup.cfg

echo "[install]" > ./setup.cfg
echo "prefix= " >> ./setup.cfg

# Try and handle failure if pip version mismatch
if [ -x "$(command -v pip)" ]; then
  pip install -r ../requirements.txt --target .

elif [ -x "$(command -v pip3)" ]; then
  echo "pip not found, trying with pip3"
  pip3 install -r ../requirements.txt --target .

elif ! [ -x "$(command -v pip)" ] && ! [ -x "$(command -v pip3)" ]; then
 echo "No version of pip installed. This script requires pip. Cleaning up and exiting."
 exit 1
fi

if ! [ -d ../dist/start_translate.zip ]; then
  zip -r9 ../dist/start_translate.zip .

elif [ -d ../dist/start_translate.zip ]; then
  echo "Package already present"
fi

popd

zip -g dist/start_translate.zip start_translate.py awsmie.py

cp "./dist/start_translate.zip" "$dist_dir/start_translate.zip"

echo "------------------------------------------------------------------------------"
echo "Polly  Operations"
echo "------------------------------------------------------------------------------"

echo "Building Stage completion function"
cd "$source_dir/operations/polly" || exit

[ -e dist ] && rm -r dist
mkdir -p dist

[ -e package ] && rm -r package
mkdir -p package

echo "create requirements for lambda"

#pipreqs . --force

# Make lambda package

pushd package
echo "create lambda package"

# Handle distutils install errors

touch ./setup.cfg

echo "[install]" > ./setup.cfg
echo "prefix= " >> ./setup.cfg

# Try and handle failure if pip version mismatch
if [ -x "$(command -v pip)" ]; then
  pip install -r ../requirements.txt --target .

elif [ -x "$(command -v pip3)" ]; then
  echo "pip not found, trying with pip3"
  pip3 install -r ../requirements.txt --target .

elif ! [ -x "$(command -v pip)" ] && ! [ -x "$(command -v pip3)" ]; then
 echo "No version of pip installed. This script requires pip. Cleaning up and exiting."
 exit 1
fi

if ! [ -d ../dist/start_polly.zip ]; then
  zip -r9 ../dist/start_polly.zip .

elif [ -d ../dist/start_polly.zip ]; then
  echo "Package already present"
fi

if ! [ -d ../dist/get_polly.zip ]; then
  zip -r9 ../dist/get_polly.zip .

elif [ -d ../dist/get_polly.zip ]; then
  echo "Package already present"
fi


popd

zip -g dist/start_polly.zip start_polly.py awsmie.py
zip -g dist/get_polly.zip get_polly.py awsmie.py

cp "./dist/start_polly.zip" "$dist_dir/start_polly.zip"
cp "./dist/get_polly.zip" "$dist_dir/get_polly.zip"

echo "------------------------------------------------------------------------------"
echo "Comprehend  Operations"
echo "------------------------------------------------------------------------------"

echo "Building Stage completion function"
cd "$source_dir/operations/comprehend" || exit

[ -e dist ] && rm -r dist
mkdir -p dist

[ -e package ] && rm -r package
mkdir -p package

echo "create requirements for lambda"

#pipreqs . --force

# Make lambda package

pushd package
echo "create lambda package"

# Handle distutils install errors

touch ./setup.cfg

echo "[install]" > ./setup.cfg
echo "prefix= " >> ./setup.cfg

# Try and handle failure if pip version mismatch
if [ -x "$(command -v pip)" ]; then
  pip install -r ../requirements.txt --target .

elif [ -x "$(command -v pip3)" ]; then
  echo "pip not found, trying with pip3"
  pip3 install -r ../requirements.txt --target .

elif ! [ -x "$(command -v pip)" ] && ! [ -x "$(command -v pip3)" ]; then
 echo "No version of pip installed. This script requires pip. Cleaning up and exiting."
 exit 1
fi

if ! [ -d ../dist/start_key_phrases.zip ]; then
  zip -r9 ../dist/start_key_phrases.zip .

elif [ -d ../dist/start_key_phrases.zip ]; then
  echo "Package already present"
fi

if ! [ -d ../dist/get_key_phrases.zip ]; then
  zip -r9 ../dist/get_key_phrases.zip .

elif [ -d ../dist/get_key_phrases.zip ]; then
  echo "Package already present"
fi


popd

zip -g dist/start_key_phrases.zip start_key_phrases.py awsmie.py
zip -g dist/get_key_phrases.zip get_key_phrases.py awsmie.py

cp "./dist/start_key_phrases.zip" "$dist_dir/start_key_phrases.zip"
cp "./dist/get_key_phrases.zip" "$dist_dir/get_key_phrases.zip"

echo "------------------------------------------------------------------------------"
echo "Stage Completion Function"
echo "------------------------------------------------------------------------------"

echo "Building Stage completion function"
cd "$source_dir/workflow" || exit

[ -e dist ] && rm -r dist
mkdir -p dist

[ -e package ] && rm -r package
mkdir -p package

echo "Create requirements for lambda"

#pipreqs . --force

# Make lambda package
pushd package
echo "Create lambda package"

# Handle distutils install errors

touch ./setup.cfg

echo "[install]" > ./setup.cfg
echo "prefix= " >> ./setup.cfg

# Try and handle failure if pip version mismatch
if [ -x "$(command -v pip)" ]; then
  pip install -r ../requirements.txt --target .

elif [ -x "$(command -v pip3)" ]; then
  echo "pip not found, trying with pip3"
  pip3 install -r ../requirements.txt --target .

elif ! [ -x "$(command -v pip)" ] && ! [ -x "$(command -v pip3)" ]; then
  echo "No version of pip installed. This script requires pip. Cleaning up and exiting."
  exit 1
fi

zip -r9 ../dist/workflow.zip .

popd

zip -g dist/workflow.zip *.py

cp "./dist/workflow.zip" "$dist_dir/workflow.zip"


echo "------------------------------------------------------------------------------"
echo "Workflow API Function"
echo "------------------------------------------------------------------------------"
echo "Building Workflow Lambda function"
cd "$source_dir/workflow-api" || exit

prefix="media-analysis-solution/$2/code"


[ -e dist ] && rm -r dist
mkdir -p dist

if ! [ -x "$(command -v chalice)" ]; then
  echo 'Chalice is not installed. It is required for this solution. Exiting.'
  exit 1
fi


chalice package dist
./chalice-fix-inputs.py
aws cloudformation package --template-file dist/sam.json --s3-bucket $bucket --s3-prefix $prefix --output-template-file "dist/workflowapi_sam.yaml" --profile default

# Need to add something here to ensure docopt and aws-sam-translator are present
./sam-translate.py


echo "cp ./dist/workflowapi.yaml $template_dir/media-analysis-workflow-api-stack.yaml"
cp dist/workflowapi.yaml $template_dir/media-analysis-workflow-api-stack.yaml

echo "cp $template_dir/media-analysis-workflow-api-stack.yaml $dist_dir/media-analysis-workflow-api-stack.template"
cp $template_dir/media-analysis-workflow-api-stack.yaml $dist_dir/media-analysis-workflow-api-stack.template


echo "------------------------------------------------------------------------------"
echo "Dataplane API Stack"
echo "------------------------------------------------------------------------------"
echo "Building Dataplane Stack"
cd "$source_dir/dataplane-api" || exit

prefix="media-analysis-solution/$2/code"

[ -e dist ] && rm -r dist
mkdir -p dist

if ! [ -x "$(command -v chalice)" ]; then
  echo 'Chalice is not installed. It is required for this solution. Exiting.'
  exit 1
fi


chalice package dist
./chalice-fix-inputs.py
aws cloudformation package --template-file dist/sam.json --s3-bucket $bucket --s3-prefix $prefix --output-template-file "dist/dataplaneapi_sam.yaml" --profile default

# Need to add something here to ensure docopt and aws-sam-translator are present
./sam-translate.py


echo "cp ./dist/dataplaneapi.yaml $template_dir/media-analysis-dataplane-api-stack.yaml"
cp dist/dataplaneapi.yaml $template_dir/media-analysis-dataplane-api-stack.yaml

echo "cp $template_dir/media-analysis-dataplane-api-stack.yaml $dist_dir/media-analysis-dataplane-api-stack.template"
cp $template_dir/media-analysis-dataplane-api-stack.yaml $dist_dir/media-analysis-dataplane-api-stack.template


echo "------------------------------------------------------------------------------"
echo "Test Operations"
echo "------------------------------------------------------------------------------"

echo "Building Stage completion function"
cd "$source_dir/operations/test" || exit

[ -e dist ] && rm -r dist
mkdir -p dist

[ -e package ] && rm -r package
mkdir -p package

echo "create requirements for lambda"

#pipreqs . --force

# Make lambda package

pushd package
echo "create lambda package"

# Handle distutils install errors

touch ./setup.cfg

echo "[install]" > ./setup.cfg
echo "prefix= " >> ./setup.cfg

# Try and handle failure if pip version mismatch
if [ -x "$(command -v pip)" ]; then
  pip install -r ../requirements.txt --target .

elif [ -x "$(command -v pip3)" ]; then
  echo "pip not found, trying with pip3"
  pip3 install -r ../requirements.txt --target .

elif ! [ -x "$(command -v pip)" ] && ! [ -x "$(command -v pip3)" ]; then
 echo "No version of pip installed. This script requires pip. Cleaning up and exiting."
 exit 1
fi

if ! [ -d ../dist/test_operations.zip ]; then
  zip -r9 ../dist/test_operations.zip .

elif [ -d ../dist/test_operations.zip ]; then
  echo "Package already present"

fi

popd

zip -g dist/test_operations.zip *.py

cp "./dist/test_operations.zip" "$dist_dir/test_operations.zip"

echo "------------------------------------------------------------------------------"
echo "Building Lambda Layers"
echo "------------------------------------------------------------------------------"
cp $source_dir/lambda_layers/boto3-python3.7.zip $dist_dir/

echo "------------------------------------------------------------------------------"
echo "Analysis2 Function"
echo "------------------------------------------------------------------------------"
echo "Building Analysis Lambda function"
cd "$source_dir/analysis2" || exit
npm install
npm run build
npm run zip
cp "./dist/media-analysis-function2.zip" "$dist_dir/media-analysis-function2.zip"

echo "------------------------------------------------------------------------------"
echo "Preprocess Function"
echo "------------------------------------------------------------------------------"
echo "Building Preprocess Lambda function"
cd "$source_dir/preprocess" || exit
npm install
npm run build
npm run zip
cp "./dist/media-analysis-preprocess-function.zip" "$dist_dir/media-analysis-preprocess-function.zip"

# MAS 1.0 operations

: '''

echo "------------------------------------------------------------------------------"
echo "Analysis Function"
echo "------------------------------------------------------------------------------"
echo "Building Analysis Lambda function"
cd "$source_dir/analysis" || exit
npm install
npm run build
npm run zip
cp "./dist/media-analysis-function.zip" "$dist_dir/media-analysis-function.zip"

echo "------------------------------------------------------------------------------"
echo "API Function"
echo "------------------------------------------------------------------------------"
echo "Building API Lambda function"
cd "$source_dir/api" || exit
npm install
npm run build
npm run zip
cp "./dist/media-analysis-api.zip" "$dist_dir/media-analysis-api.zip"

echo "------------------------------------------------------------------------------"
echo "Helper Function"
echo "------------------------------------------------------------------------------"
echo "Building Helper Lambda function"
cd "$source_dir/helper" || exit
npm install
npm run build
npm run zip
cp "./dist/media-analysis-helper.zip" "$dist_dir/media-analysis-helper.zip"


echo "------------------------------------------------------------------------------"
echo "Website"
echo "------------------------------------------------------------------------------"
echo "Building Demo Website"
cd "$source_dir/web_site" || exit
npm install
npm run build
cp -r "./build" "$dist_dir/web_site"

echo "------------------------------------------------------------------------------"
echo "Website Manifest"
echo "------------------------------------------------------------------------------"
echo "Generating web site manifest"
cd "$template_dir/manifest-generator" || exit
npm install
node app.js --target "$dist_dir/web_site" --output "$dist_dir/site-manifest.json"

'''

echo "------------------------------------------------------------------------------"
echo "Copy dist to S3"
echo "------------------------------------------------------------------------------"

# Task to upload code to newly created S3 bucket

echo "We are copying in your source into the S3 bucket"

for file in $dist_dir/*.zip
do
     echo $file
     aws s3 cp $file s3://$bucket/media-analysis-solution/$2/code/
 done

 for file in $dist_dir/*.template
 do
     echo $file
     aws s3 cp $file s3://$bucket/media-analysis-solution/$2/cf/
 done


echo "------------------------------------------------------------------------------"
echo "S3 Packaging Complete"
echo "------------------------------------------------------------------------------"


echo "------------------------------------------------------------------------------"
echo "Cleaning up"
echo "------------------------------------------------------------------------------"

# Add cleanup routine


echo "------------------------------------------------------------------------------"
echo "Done"
echo "------------------------------------------------------------------------------"