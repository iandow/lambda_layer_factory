from chalice import Chalice
from chalice import NotFoundError, BadRequestError, ChaliceViewError, Response, ConflictError
from botocore.client import ClientError

import boto3
import os
import decimal
import uuid
import json
import logging

# TODO: Add additional exception and response codes

logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)

APP_NAME = 'dataplane-api'
app = Chalice(app_name=APP_NAME)

# DDB resources
# TODO: Get this env variable working
# DATAPLANE_TABLE_NAME = os.environ['DATAPLANE_TABLE_NAME']
DATAPLANE_TABLE_NAME = 'mas_dataplane_test'
DYNAMO_CLIENT = boto3.client('dynamodb')
DYNAMO_RESOURCE = boto3.resource('dynamodb')

# S3 resources
# TODO: Get this env variable working
# DATAPLANE_S3_BUCKET = os.environ['DATAPLANE_BUCKET_NAME']
DATAPLANE_S3_BUCKET = 'dataplane-testing-v1'

# TODO: Should we add a variable for the upload bucket?

BASE_S3_URI = 'private/media/'
S3_CLIENT = boto3.client('s3')

# Helper class to convert a DynamoDB item to JSON.


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


def checkRequiredInput(key, dict, objectname):
    if key not in dict:
        raise BadRequestError("Key '%s' is required in '%s' input" % (
            key, objectname))


@app.route('/')
def index():
    return {'hello': 'world'}


@app.route('/data/create', cors=True, methods=['POST'])
def create_asset():
    # TODO: Maybe add some checking if asset id exists? I dont know... should chat about this
    """
    Create an asset in the dataplane from a json input composed of the input key and bucket of the object

    Body:
    {
        "input": {
            "s3bucket": "{somenbucket}",
            "s3key": "{somekey}"
        }
    }

    Returns:
        A dict mapping of the asset id and the new location of the media object

    Raises:
        500: Internal server erro
        ...
    """
    # TODO: Maybe carry additional data in api call?

    table_name = DATAPLANE_TABLE_NAME
    bucket = DATAPLANE_S3_BUCKET
    uri = BASE_S3_URI

    asset = app.current_request.json_body
    logger.info(asset)

    # create a uuid for the asset

    asset_id = str(uuid.uuid4())

    # check required inputs

    try:
        checkRequiredInput("s3bucket",  asset['input'], "asset creation")
        checkRequiredInput("s3key", asset['input'], "asset creation")
    except Exception as e:
        logger.error("Exception {}".format(e))
        raise ChaliceViewError("Exception: {e}".format(e=e))

    # build key structure for dataplane object

    key = uri + asset_id + "/"

    # create directory structure in s3 dataplane bucket for the asset

    try:
        S3_CLIENT.put_object(
            Bucket=bucket,
            Key=key
        )
    except Exception as e:
        logger.error("Exception {}".format(e))
        raise ChaliceViewError("Exception: {e}".format(e=e))

    # build location of the source object a key for the new object

    source_key = asset['input']['s3key']
    source_bucket = asset['input']['s3bucket']
    new_key = key + 'input' + '/' + source_key

    # copy input media into newly created dataplane s3 hierarchy

    try:
        S3_CLIENT.copy_object(
            Bucket=DATAPLANE_S3_BUCKET,
            Key=new_key,
            CopySource={'Bucket': source_bucket, 'Key': source_key}
        )
    except Exception as e:
        logger.error("Exception {}".format(e))
        raise ChaliceViewError("Exception: {e}".format(e=e))

    # build ddb item of the asset

    try:
        table = DYNAMO_RESOURCE.Table(table_name)
        table.put_item(
            Item={
                "asset_id": asset_id,
                "s3bucket": DATAPLANE_S3_BUCKET,
                "s3key": new_key
            }
        )
    except Exception as e:
        logger.error("Exception {}".format(e))
        raise ChaliceViewError("Exception: {e}".format(e=e))

    return {"asset_id": asset_id, "s3bucket": DATAPLANE_S3_BUCKET, "s3key": new_key}

@app.route('/data/{asset_id}', cors=True, methods=['POST'])
def put_asset_metadata(asset_id):
    """
    Adds operation metadata for an asset

    Body:
    {
        "operator_name": "{some_operator}",
        "results": "{json_formatted_results}"
    }

    Returns:
        Nothing yet
    Raises:
        200
        ...
    """

    metadata = app.current_request.json_body
    logger.info(metadata)

    # check required inputs

    try:
        checkRequiredInput("operator_name", metadata, "metadata")
        checkRequiredInput("results", metadata, "metadata")
    except Exception as e:
        logger.error("Exception {}".format(e))
        raise ChaliceViewError("Exception: {e}".format(e=e))

    operator_name = metadata['operator_name']
    results = metadata['results']
    table_name = DATAPLANE_TABLE_NAME
    asset = asset_id

    # Verify asset exists before adding metadata

    try:
        table = DYNAMO_RESOURCE.Table(table_name)
        response = table.get_item(
            Key={
                "asset_id": asset
            }
        )
    except ClientError as e:
        raise ChaliceViewError("Exception: {e}".format(e=e))
    else:
        if 'Item' not in response:
            raise ChaliceViewError("Exception: Asset does not exist")

    operator_attribute = operator_name + "_" + "result"

    try:
        table = DYNAMO_RESOURCE.Table(table_name)
        table.update_item(
            Key={
                "asset_id": asset
            },
            UpdateExpression="SET #operator_result = :result",
            ExpressionAttributeNames={"#operator_result": operator_attribute},
            ExpressionAttributeValues={":result": results},
        )
    except Exception as e:
        logger.error("Exception {}".format(e))
        raise ChaliceViewError("Exception: {e}".format(e=e))

    return "Added {name} results for the following asset: {asset}".format(name=operator_name, asset=asset)


