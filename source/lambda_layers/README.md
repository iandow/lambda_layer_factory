# Instructions for building AWS Lambda layers

Media analysis operators are implemented as AWS Lambda functions. These functions should access library dependencies via Lambda layers so that you can:

* explicitly control which library versions your operator uses, and 
* avoid monolithic Lambda functions which are unnecessarily large, slow to deploy, and unable to be rendered in the AWS Lambda code editor.

The procedure below explains how to create a Lambda layer for any Python library:

### Prerequisites: 
1. Install [Docker](https://docs.docker.com/docker-for-mac/install/) on your workstation.


### Build ZIP files for Lambda layers using Docker

AWS Lambda functions run in an [Amazon Linux environment](https://docs.aws.amazon.com/lambda/latest/dg/current-supported-versions.html), so libraries should be built for Amazon Linux. You can build Python libraries for Amazon Linux using Docker, as described below:

1. First, get the provided Dockerfile:
```
git clone https://code.amazon.com/packages/MediaAnalysisSolution
cd MediaAnalysisSolution/source/lambda_layers
```

2. Edit the Dockerfile and update each reference to OpenCV to specify the Python libraries you want to include in the Lambda layer. The rest of these instructions will assume you are packaging OpenCV as it's defined in the original Dockerfile.

3. Build and run the Docker image:
```
docker build --tag=lambda-layer-factory:latest .
docker run --rm -it -v $(pwd):/data lambda-layer-factory cp /packages/cv2-python36.zip /data
```

4. Ensure the docker generated zip file is saved in the `lambda_layers/` directory. The `build-s3-dist-copy.sh` script will look for them there, copy them to S3, and automatically generate the layer.

For more information, see [https://github.com/iandow/opencv_aws_lambda](https://github.com/iandow/opencv_aws_lambda)
