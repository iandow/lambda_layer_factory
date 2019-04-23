# AWS Lambda Layer factory

This project creates AWS Lambda layers for user-specified Python libraries. Two seperate zip files will be generated for Python 3.6 and 3.7 execution environments.

## USAGE:

### Preliminary Setup: 
1. Install [Docker](https://docs.docker.com/) and the [AWS CLI](https://aws.amazon.com/cli/) on your workstation.
2. Setup credentials for AWS CLI (see http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html).
3. Create IAM Role with Lambda and S3 access:
```
# Create a role with S3 access
ROLE_NAME=lambda_layer_factory
aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document '{"Version":"2012-10-17","Statement":{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}}'
aws iam attach-role-policy --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess --role-name $ROLE_NAME
```

### Build Lambda layers
Download this repo.
```
git clone https://github.com/iandow/lambda_layer_factory
cd lambda_layer_factory
```

Put your desired Python libraries in a requirements.txt file, following standard pip conventions. For example:
```
echo "boto3==1.9.134" >> requirements.txt
echo "chalice==1.8.0" >> requirements.txt
```

Build the Lamber layer zip files and copy them to your current directory like this:
```
docker build --tag=lambda_layer_factory:latest .
docker run --rm -it -v $(pwd):/packages lambda_layer_factory
```

### Publish Lambda layers
Publish Lambda layers to your AWS account like this:
```
ACCOUNT_ID=$(aws sts get-caller-identity --output text --query 'Account')
LAMBDA_LAYERS_BUCKET=lambda-layers-$ACCOUNT_ID
LAYER_NAME=lambda_layer-python36
aws s3 mb s3://$LAMBDA_LAYERS_BUCKET
aws s3 cp lambda_layer-python3.6.zip s3://$LAMBDA_LAYERS_BUCKET
aws lambda publish-layer-version --layer-name $LAYER_NAME --content S3Bucket=$LAMBDA_LAYERS_BUCKET,S3Key=lambda_layer-python3.6.zip --compatible-runtimes python3.6
LAYER_NAME=lambda_layer-python37
aws s3 cp lambda_layer-python3.7.zip s3://$LAMBDA_LAYERS_BUCKET
aws lambda publish-layer-version --layer-name $LAYER_NAME --content S3Bucket=$LAMBDA_LAYERS_BUCKET,S3Key=lambda_layer-python3.7.zip --compatible-runtimes python3.7
```

Validate that the Lambda layers were created
```
aws lambda list-layer-versions --layer-name lambda_layer-python36 --output text --query 'LayerVersions[0].LayerVersionArn'
aws lambda list-layer-versions --layer-name lambda_layer-python37 --output text --query 'LayerVersions[0].LayerVersionArn'
```
### Clean up build environment
```
aws s3 rm s3://$LAMBDA_LAYERS_BUCKET/lambda_layer-python3.6.zip
aws s3 rm s3://$LAMBDA_LAYERS_BUCKET/lambda_layer-python3.7.zip
aws s3 rb s3://$LAMBDA_LAYERS_BUCKET/
aws iam detach-role-policy --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess --role-name $ROLE_NAME
aws iam delete-role --role-name $ROLE_NAME
```
