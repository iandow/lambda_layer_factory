#!/bin/bash

echo "================================================================================"
echo "Installing packages from requirements.txt"
echo "================================================================================"
pip3.7 install -r /packages/requirements.txt -t /packages/lambda_layer-python-3.7/python/lib/python3.7/site-packages
pip3.6 install -r /packages/requirements.txt -t /packages/lambda_layer-python-3.6/python/lib/python3.6/site-packages

echo "================================================================================"
echo "Creating zip files for Lambda layers"
echo "================================================================================"
cd /packages/lambda_layer-python-3.7/
zip -q -r9 /packages/lambda_layer-python3.7.zip .
cd /packages/lambda_layer-python-3.6/
zip -q -r9 /packages/lambda_layer-python3.6.zip .

cd /packages/
# Verify the deployment package meets AWS Lambda layer size limits.
# see https://docs.aws.amazon.com/lambda/latest/dg/limits.html
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

# Clean up build environment
rm -rf /packages/lambda_layer-python-3.6/
rm -rf /packages/lambda_layer-python-3.7/

echo "Zip files have been saved to docker volume /data. You can copy them locally like this:"
echo "docker run --rm -it -v \$(pwd):/packages <docker_image>"
echo "================================================================================"
echo "Done."
