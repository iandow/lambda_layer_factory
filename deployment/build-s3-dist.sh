#!/bin/bash

# This assumes all of the OS-level configuration has been completed and git repo has already been cloned

# This script should be run from the repo's deployment directory
# cd deployment
# ./build-s3-dist.sh source-bucket-base-name
# source-bucket-base-name should be the base name for the S3 bucket location where the template will source the Lambda code from.
# The template will append '-[region_name]' to this bucket name.
# For example: ./build-s3-dist.sh solutions
# The template will then expect the source code to be located in the solutions-[region_name] bucket

# Check to see if input has been provided:
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Please provide the base source bucket name and version where the lambda code will eventually reside."
    echo "For example: ./build-s3-dist.sh solutions v1.0.0"
    exit 1
fi



# Get reference for all important folders
template_dir="$PWD"
dist_dir="$template_dir/dist"
source_dir="$template_dir/../source"

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
echo "CloudFormation Templates"
echo "------------------------------------------------------------------------------"
# Copy deploy template to dist directory and update bucket name
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

echo "Updating code source bucket in template with '$1'"
replace="s/%%BUCKET_NAME%%/$1/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-api-stack.template"
sed -i '' -e $replace "$dist_dir/media-analysis-api-stack.template"

echo "Replacing solution version in template with '$2'"
replace="s/%%VERSION%%/$2/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-api-stack.template"
sed -i '' -e $replace "$dist_dir/media-analysis-api-stack.template"

# Copy workflow template to dist directory and update bucket name
echo "Replacing solution version in template with '$2'"
replace="s/%%VERSION%%/$2/g"
echo "cp $template_dir/media-analysis-workflow-stack.yaml $dist_dir/media-analysis-workflow-stack.template"
cp "$template_dir/media-analysis-workflow-stack.yaml" "$dist_dir/media-analysis-workflow-stack.template"

echo "Updating code source bucket in template with '$1'"
replace="s/%%BUCKET_NAME%%/$1/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-workflow-stack.template"
sed -i '' -e $replace "$dist_dir/media-analysis-workflow-stack.template"

echo "Replacing solution version in template with '$2'"
replace="s/%%VERSION%%/$2/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-workflow-stack.template"
sed -i '' -e $replace "$dist_dir/media-analysis-workflow-stack.template"

# Copy test operations template to dist directory and update bucket name
echo "Replacing solution version in template with '$2'"
replace="s/%%VERSION%%/$2/g"
echo "cp $template_dir/media-analysis-test-operations-stack.yaml $dist_dir/media-analysis-test-operations-stack.template"
cp "$template_dir/media-analysis-test-operations-stack.yaml" "$dist_dir/media-analysis-test-operations-stack.template"

echo "Updating code source bucket in template with '$1'"
replace="s/%%BUCKET_NAME%%/$1/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-test-operations-stack.template"
sed -i '' -e $replace "$dist_dir/media-analysis-test-operations-stack.template"

echo "Replacing solution version in template with '$2'"
replace="s/%%VERSION%%/$2/g"
echo "sed -i '' -e $replace $dist_dir/media-analysis-test-operations-stack.template"
sed -i '' -e $replace "$dist_dir/media-analysis-test-operations-stack.template"

# Copy storage template to dist directory and update bucket name
echo "cp $template_dir/media-analysis-storage-stack.yaml $dist_dir/media-analysis-storage-stack.template"
cp "$template_dir/media-analysis-storage-stack.yaml" "$dist_dir/media-analysis-storage-stack.template"

# Copy state machine template to dist directory
echo "cp $template_dir/media-analysis-state-machine-stack.yaml $dist_dir/media-analysis-state-machine-stack.template"
cp "$template_dir/media-analysis-state-machine-stack.yaml" "$dist_dir/media-analysis-state-machine-stack.template"

# Copy state machine template to dist directory
echo "cp $template_dir/media-analysis-preprocess-state-machine-stack.yaml $dist_dir/media-analysis-preprocess-state-machine-stack.template"
cp "$template_dir/media-analysis-preprocess-state-machine-stack.yaml" "$dist_dir/media-analysis-preprocess-state-machine-stack.template"

echo "------------------------------------------------------------------------------"
echo "Stage Completion Function"
echo "------------------------------------------------------------------------------"

echo "Building Stage completion function"
cd "$source_dir/workflow" || exit

[ -e dist ] && rm -r dist
mkdir -p dist

[ -e package ] && rm -r package
mkdir -p package

echo "create requirements for lambda"

#pipreqs . --force

# Make lambda package
pushd package
echo "create lambda package"
pip install -r ../requirements.txt --target .
zip -r9 ../dist/workflow.zip . 
popd
zip -g dist/workflow.zip *.py

cp "./dist/workflow.zip" "$dist_dir/workflow.zip"


echo "------------------------------------------------------------------------------"
echo "Workflow API Function"
echo "------------------------------------------------------------------------------"
echo "Building Workflow Lambda function"
cd "$source_dir/workflow-api" || exit

bucket="$1-us-east-1"
prefix="media-analysis-solution/$2"

[ -e dist ] && rm -r dist
mkdir -p dist

chalice package dist
./chalice-fix-inputs.py
aws cloudformation package --template-file dist/sam.json --s3-bucket $bucket --s3-prefix $prefix --output-template-file "dist/workflowapi_sam.yaml" --profile default
./sam-translate.py


echo "cp ./dist/workflowapi.yaml $template_dir/media-analysis-workflow-api-stack.yaml"
cp dist/workflowapi.yaml $template_dir/media-analysis-workflow-api-stack.yaml

echo "cp $template_dir/media-analysis-workflow-api-stack.yaml $dist_dir/media-analysis-workflow-api-stack.template"
cp $template_dir/media-analysis-workflow-api-stack.yaml $dist_dir/media-analysis-workflow-api-stack.template

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
pip install -r ../requirements.txt --target .
zip -r9 ../dist/test_operations.zip . 
popd
zip -g dist/test_operations.zip *.py

cp "./dist/test_operations.zip" "$dist_dir/test_operations.zip"

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

echo "------------------------------------------------------------------------------"
echo "S3 Packaging Complete"
echo "------------------------------------------------------------------------------"
