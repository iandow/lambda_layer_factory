# Media Analysis Solution
The increasing maturity and growing availability of machine learning (ML) algorithms and artificial intelligence (AI) services have unlocked new frontiers in analytics across several forms of media. Through the use of AI tools and services, it is possible to detect objects, recognize faces, transcribe and analyze audio, and much more. Advancements in deep learning algorithms and AI tooling have enabled developers and analysts to efficiently extract valuable data from multimedia sources, but can still require a great deal of time and effort to train ML models as well as maintain supporting infrastructure.

AWS offers several managed AI services, such as Amazon Rekognition, Amazon Transcribe, and Amazon Comprehend, that offer immediate insights into image, video, and audio files. By combining these services with Amazon's managed storage and compute services, customers can quickly and easily build intelligent applications that inform and enable many use cases across a variety of fields, including public safety and security, media and entertainment, advertising and social media, etc.

The Media Analysis Solution is a turnkey reference implementation that helps customers start analyzing their media files using serverless, managed AI services. The Media Analysis Solution uses highly available, highly scalable, and highly accurate AWS-native services to automatically extract valuable metadata from audio, image, and video files.

For more information and a detailed deployment guide visit the Media Analysis Solution at https://aws.amazon.com/answers/media-entertainment/media-analysis-solution/.

## Prerequisites: 
Install the Node version 9. This is easiest with the [node version manager](https://github.com/creationix/nvm) (nvm), like this:
```
curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
source ~/.bashrc
nvm install 9
nvm use 9
node --version # should say v9.11.2
npm -version # should say 5.6.0
```

Install and setup credentials for the AWS CLI (see http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html).

## Running unit tests for customization
* Clone the repository, then make the desired code changes
* Next, run unit tests to make sure added customization passes the tests
```
cd ./deployment
chmod +x ./run-unit-tests.sh
./run-unit-tests.sh
```

## Build and deploy Cloud Formation templates
* Configure the bucket name of your target Amazon S3 distribution bucket
```
export DIST_OUTPUT_BUCKET=my-bucket-name # bucket where customized code will reside
export VERSION=my-version # version number for the customized code
```
_Note:_ You would have to create an S3 bucket with the prefix 'my-bucket-name-<aws_region>'; aws_region is where you are testing the customized solution. Also, the assets in bucket should be publicly accessible.

* Now build the distributable:
```
chmod +x ./build-s3-dist.sh
./build-s3-dist.sh $DIST_OUTPUT_BUCKET $VERSION
```

* Deploy the distributable to an Amazon S3 bucket in your account. _Note:_ you must have the AWS Command Line Interface installed.
```
aws s3 cp ./dist/ s3://my-bucket-name-<aws_region>/media-analysis-solution/<my-version>/ --recursive --acl bucket-owner-full-control --profile aws-cred-profile-name
```

* Get the link of the media-analysis-deploy.template uploaded to your Amazon S3 bucket.
* Deploy the Media Analysis Solution to your account by launching a new AWS CloudFormation stack using the link of the media-analysis-deploy.template.

## File Structure
The Media Analysis Solution consists of a demo website, an analysis orchestration layer, a search and storage layer, and an API layer.
* The demo website is a React application that leverages AWS Amplify to interact with Amazon S3, Amazon API Gateway, and Amazon Cognito.
* The analysis orchestration layer is an AWS Step Functions state machine that coordinates metadata extraction from Amazon AI services.
* The search and storage layer uses Amazon Elasticsearch to index extracted metadata and handle search requests.
* The API layer handles requests for details of media files.
* The microservices are deployed to a serverless environment in AWS Lambda.

```
|-deployment/
  |-buildspecs/                             [ solutions builder pipeline build specifications ]
  |-build-s3-dist.sh                        [ shell script for packaging distribution assets ]
  |-run-unit-tests.sh                       [ shell script for executing unit tests ]
  |-media-analysis-deploy.yaml              [ solution CloudFormation deployment template ]
  |-media-analysis-api-stack.yaml           [ solution CloudFormation template for deploying API services ]
  |-media-analysis-storage-stack.yaml       [ solution CloudFormation template for deploying storage services ]
  |-media-analysis-state-machine-stack.yaml [ solution CloudFormation template for deploying state machine ]
|-source/
  |-analysis/                               [ microservices for orchestrating media analysis ]
    |-lib/
      |-collection/                         [ microservice for indexing a new face in a Amazon Rekognition collection ]
      |-comprehend/                         [ microservice for orchestrating natural language comprehension tasks ]
      |-elasticsearch/                      [ microservice for indexing extracted metadata in Amazon Elasticsearch cluster ]
      |-image/                              [ microservice for orchestrating image analysis ]
      |-metricsHelper/                      [ microservice for capturing anonymous metrics pertinent for feedback on the solution ]
      |-steps/                              [ microservice for starting the state machine ]
      |-transcribe/                         [ microservice for orchestrating audio transcription ]
      |-upload/                             [ microservice for uploading metadata to Amazon S3 ]
      |-video/                              [ microservice for orchestrating video analysis ]
    |-index.js
    |-package.json
  |-api/                                    [ microservice for handling requests from Amazon API Gateway ]
    |-lib/
      |-index.js                            [ injection point for microservice ]
      |-details.js                          [ returns details for a requested media file ]
      |-lookup.js                           [ returns metadata for a requested media file ]
      |-search.js                           [ performs a search on Amazon Elasticsearch cluster ]
      |-status.js                           [ returns status of media analysis state machine ]
      |-[service unit tests]
    |-index.js
    |-package.json
  |-helper/                                 [ AWS CloudFormation custom resource for aiding the deployment of the solution ]
    |-lib/
      |-index.js                            [ injection point for microservice ]
      |-esHelper.js                         [ helper for interacting with Amazon Elasticsearch cluster ]
      |-metricsHelper.js                    [ helper for capturing anonymous metrics pertinent for feedback on the solution ]
      |-s3helper.js                         [ helper for interacting with Amazon S3 ]
    |-index.js
    |-package.json
  |-web_site/                               [ ReactJS demo website for the solution ]
    |-public/                               
    |-src/                                  
      |-components/                         
      |-img/
      |-styles/
    |-package.json
```

Each microservice in analysis/lib/ follows the structure of:

```
|-service-name/
  |-index.js [injection point for microservice]
  |-[service-specific code]
  |-[service-name].js
```

# Instructions for Building Custom Operators

This section explains how to build custom operators as AWS Lambda functions using Python. We recommend packaging library dependencies as Lambda Layers because they make Lambda functions smaller, which makes them faster to build and easier to view in the AWS Lambda in-browser code editor.

There are two important [AWS Lambda Limits](https://docs.aws.amazon.com/lambda/latest/dg/limits.html) to be aware of:
* A function can use no more than 5 layers at a time. 
* The total unzipped size of the function and all layers must be smaller than 250 MB. 

*The following steps build a boilerplate operator as a Python3 lambda function using the boto3 library as a lambda layer.*

## Prerequisites:

* Install `jq` (see [https://stedolan.github.io/jq/download/](https://stedolan.github.io/jq/download/)).
* Install and setup credentials for the AWS CLI (see http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html)

## Step 1 - Create the AWS Lambda function
Package the source code for your lambda function into a zip file and deploy it:
```
FUNCTION_NAME=mas2-test3-test-video
REGION=us-west-2

cd ./source/operations/test/
zip -g test.zip test.py
aws lambda create-function --function-name $FUNCTION_NAME --timeout 10 --handler app.lambda_handler --region $REGION --zip-file fileb://./test.zip --runtime python3.6
# Now remove the zip file since we're done with it
rm test.zip
```

## Step 2 - Create a AWS Lambda Layer for boto3
Build boto3 in a temporary virtualenv environment. Specify a specific boto3 version (as opposed to using latest) in order to keep the dependency in constant state.

```
LAYER_NAME=boto3

virtualenv --no-site-packages venv
source venv/bin/activate
PY_DIR='build/python/lib/python3.6/site-packages'
mkdir -p $PY_DIR
echo "boto3==1.9.130" > requirements.txt
pip install -r requirements.txt -t $PY_DIR
cd build
ZIPFILE=${LAYER_NAME}_layer.zip
zip -r ../$ZIPFILE_layer.zip .
cd ..
deactivate
# Remove the build files since we don't need them anymore
rm -rf venv build
```

## Step 3 - Verify the Lambda Layer size
Some libraries can be quite large (e.g. python-opencv). So, verify the Lambda Layer complies with limits (see https://docs.aws.amazon.com/lambda/latest/dg/limits.html) before proceeding, otherwise you might get a deploy error later.
```
MAX_PACKAGE_SIZE=250
MAX_ZIP_SIZE=50

if [ $((`stat -f%z $ZIPFILE` / 1000 / 1000)) -gt $MAX_ZIP_SIZE ]; then echo "ERROR: Zip file must be less than 50MB"; fi
if [ $((`du -sm build | cut -f1`)) -gt $MAX_PACKAGE_SIZE ]; then echo "ERROR: Unzipped package must be less than 250MB"; fi
```

## Step 4 - Upload Lambda Layer

Create a bucket to hold Lambda Layers and upload to it.

```
ACCOUNT_ID=$(aws sts get-caller-identity | jq -r ".Account")
LAMBDA_LAYERS_BUCKET=lambda-layers-$ACCOUNT_ID

# Make a bucket to store lambda layers:
aws s3 mb s3://$LAMBDA_LAYERS_BUCKET
aws s3 cp $ZIPFILE s3://$LAMBDA_LAYERS_BUCKET

# Upload a lambda layer
aws lambda publish-layer-version --layer-name $LAYER_NAME --description "boto3 for Python3.6" --content S3Bucket=$LAMBDA_LAYERS_BUCKET,S3Key=$ZIPFILE --compatible-runtimes python3.6
```

## Step 5 - Attach the Lambda Layer to the Lambda Function

```
LAYER=$(aws lambda list-layer-versions --layer-name $LAYER_NAME | jq -r '.LayerVersions[0].LayerVersionArn')
aws lambda update-function-configuration --function-name $FUNCTION_NAME --layers $LAYER
```

## Step 6 - Test the Lambda Function

Invoke your lambda function to make sure it works.
```
aws lambda invoke --function-name $FUNCTION_NAME --log-type Tail --payload '{"key1":"value1", "key2":"value2"}' output.txt
cat output.txt
```

***

Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

    http://aws.amazon.com/asl/

or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.


