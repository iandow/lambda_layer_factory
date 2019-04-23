#!/bin/bash
#############################################################################
# PURPOSE: Build a lambda layer for user-specified python libraries
#
# PREREQUISITES:
#   docker, aws cli
#
# USAGE:
#   Save the python libraries you want in the lambda layer in
#   requirements.txt, then run like this:
#
#   ./build-lambda-layer.sh <path to requirements.txt> <s3 bucket path> <aws region>
#
# EXAMPLE:
#   ./build-lambda-layer.sh ./requirements.txt s3://my_bucket/lambda_layers/ us-west-2
#
#############################################################################


# Check to see if input has been provided:
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Please provide a fully qualified s3 bucket for the lambda layer code to reside and the region of the deploy."
    echo "For example: ./build-lambda-layer.sh ./requirements.txt s3://my_bucket/lambda_layers/ us-west-2"
    exit 1
fi

REQUIREMENTS_FILE=$1
S3_BUCKET=$(echo $2 | cut -f 3 -d "/")
S3_FQDN=$2
REGION=$3

# Check to see if requirements.txt file exists

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "$REQUIREMENTS_FILE does not exist"
    exit 1
fi

# Check to see if AWS CLI and Docker are installed
which docker
if [ $? -ne 0 ]; then
    echo "ERROR: install Docker before running this script"
    exit 1
fi

which aws
if [ $? -ne 0 ]; then
    echo "ERROR: install the AWS CLI before running this script"
    exit 1
fi

echo "------------------------------------------------------------------------------"
echo "Validating access to S3"
echo "------------------------------------------------------------------------------"
aws s3 mb $S3_FQDN 2>&1 > /dev/null
aws s3 ls "$S3_FQDN"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed accessing $S3_FQDN"
fi

echo "------------------------------------------------------------------------------"
echo "Building Lambda Layer zip file"
echo "------------------------------------------------------------------------------"
docker build --tag=lambda_layer_factory:latest .
docker run --rm -it -v $(pwd):/packages lambda_layer_factory
if [[ ! -f ./lambda_layer-python3.6.zip ]] || [[ ! -f ./lambda_layer-python3.7.zip ]]; then
    echo "ERROR: Failed to build lambda layer zip file."
    exit 1
fi
# Verify the deployment package meets AWS Lambda layer size limits.
# See https://docs.aws.amazon.com/lambda/latest/dg/limits.html
ZIPPED_LIMIT=50
UNZIPPED_LIMIT=250
UNZIPPED_SIZE_36=`du -sm /packages/lambda_layer-python-3.6/ | cut -f 1`
ZIPPED_SIZE_36=`du -sm /packages/lambda_layer-python3.6.zip | cut -f 1`
UNZIPPED_SIZE_37=`du -sm /packages/lambda_layer-python-3.7/ | cut -f 1`
ZIPPED_SIZE_37=`du -sm /packages/lambda_layer-python3.7.zip | cut -f 1`
if (( $UNZIPPED_SIZE_36 > $UNZIPPED_LIMIT || $ZIPPED_SIZE_36 > $ZIPPED_LIMIT || $UNZIPPED_SIZE_37 > $UNZIPPED_LIMIT || $ZIPPED_SIZE_37 > $ZIPPED_LIMIT)); then
	echo "ERROR: Deployment package exceeds AWS Lambda layer size limits.";
	rm -f /packages/lambda_layer-python3.6.zip
	rm -f /packages/lambda_layer-python3.7.zip
	rm -rf /packages/lambda_layer-python-3.6/
	rm -rf /packages/lambda_layer-python-3.7/
	exit 1
fi

echo "------------------------------------------------------------------------------"
echo "Publishing Lambda Layer"
echo "------------------------------------------------------------------------------"
ACCOUNT_ID=$(aws sts get-caller-identity --output text --query 'Account')
LAMBDA_LAYERS_BUCKET=lambda-layers-$ACCOUNT_ID
LAYER_NAME_36=lambda_layer-python36
LAYER_NAME_37=lambda_layer-python37
# Warn user if layer already exists
aws lambda list-layer-versions --layer-name $LAYER_NAME_36 | grep "\"LayerVersions\": \[\]"
if [ $? -eq 0 ]; then
    echo "WARNING: AWS Layer with name $LAYER_NAME_36 already exists."
    read -r -p "Are you sure you want to overwrite $LAYER_NAME_36? [y/N] " response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]
    then
        aws s3 mb s3://$LAMBDA_LAYERS_BUCKET
        aws s3 cp lambda_layer-python3.6.zip s3://$LAMBDA_LAYERS_BUCKET
        aws lambda publish-layer-version --layer-name $LAYER_NAME_36 --content S3Bucket=$LAMBDA_LAYERS_BUCKET,S3Key=lambda_layer-python3.6.zip --compatible-runtimes python3.6
    else
        exit 1
    fi
fi
aws lambda list-layer-versions --layer-name $LAYER_NAME_37 | grep "\"LayerVersions\": \[\]"
if [ $? -eq 0 ]; then
    echo "WARNING: AWS Layer with name $LAYER_NAME_37 already exists."
    read -r -p "Are you sure you want to overwrite $LAYER_NAME_37? [y/N] " response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]
    then
        aws s3 mb s3://$LAMBDA_LAYERS_BUCKET
        aws s3 cp lambda_layer-python3.7.zip s3://$LAMBDA_LAYERS_BUCKET
        aws lambda publish-layer-version --layer-name $LAYER_NAME_37 --content S3Bucket=$LAMBDA_LAYERS_BUCKET,S3Key=lambda_layer-python3.7.zip --compatible-runtimes python3.7
    else
        exit 1
    fi
fi

echo "Lambda layers have been published. Use the following ARNs to attach them to Lambda functions:"
aws lambda list-layer-versions --layer-name lambda_layer-python36 --output text --query 'LayerVersions[0].LayerVersionArn'
aws lambda list-layer-versions --layer-name lambda_layer-python37 --output text --query 'LayerVersions[0].LayerVersionArn'

echo "------------------------------------------------------------------------------"
echo "Cleaning up"
echo "------------------------------------------------------------------------------"

aws s3 rm s3://$LAMBDA_LAYERS_BUCKET/lambda_layer-python3.6.zip
aws s3 rm s3://$LAMBDA_LAYERS_BUCKET/lambda_layer-python3.7.zip
aws s3 rb s3://$LAMBDA_LAYERS_BUCKET/

echo "------------------------------------------------------------------------------"
echo "Done"
echo "------------------------------------------------------------------------------"