# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import urllib3
import json
import boto3
import os

''' Package for implementing operations for the AWS Media Analysis Solution
'''

base_url = os.environ['DATAPLANE_ENDPOINT']
dataplane_bucket = os.environ['DATAPLANE_BUCKET']
base_s3_key = 'private/media/'


class Status:
    WORKFLOW_STATUS_STARTED = "Started"
    WORKFLOW_STATUS_ERROR = "Error"
    WORKFLOW_STATUS_COMPLETE = "Complete"

    STAGE_STATUS_NOT_STARTED = "Not Started"
    STAGE_STATUS_STARTED = "Started"
    STAGE_STATUS_EXECUTING = "Executing"
    STAGE_STATUS_ERROR = "Error"
    STAGE_STATUS_COMPLETE = "Complete"

    OPERATION_STATUS_NOT_STARTED = "Not Started"
    OPERATION_STATUS_STARTED = "Started"
    OPERATION_STATUS_EXECUTING = "Executing"
    OPERATION_STATUS_ERROR = "Error"
    OPERATION_STATUS_COMPLETE = "Complete"


class OutputHelper:
    def __init__(self, name):
        self.name = name
        self.status = ""
        self.metadata = {}
        self.media = {}

    def return_output_object(self):
        return {"name": self.name, "status": self.status, "metadata": self.metadata, "media": self.media}

    def update_status(self, status):
        self.status = status

    def update_metadata(self, **kwargs):
        for key, value in kwargs.items():
            # TODO: Add validation here to check if item exists
            self.metadata.update({key: value})

    def update_media(self, media_type, s3bucket, s3key):
        self.media[media_type] = {"s3bucket": s3bucket, "s3key": s3key}


class MasExecutionError(Exception):
    pass


# TODO: Add better exception handing for calls to the dataplane, should handle exceptions based on response code

class DataPlane:
    def __init__(self, **kwargs):
        self.base_s3_key = 'private/media'
        self.base_url = base_url
        self.http = urllib3.PoolManager()
        if "asset_id" in kwargs:
            self.asset_id = kwargs["asset_id"]
        if "workflow_id" in kwargs:
            self.workflow_id = kwargs["workflow_id"]

    def create_asset(self, s3bucket, s3key):
        body = json.dumps({
            "input": {
                "s3bucket": s3bucket,
                "s3key": s3key
            }
        })

        url = self.base_url + 'data/' + 'create'

        try:
            response = self.http.request('POST', url, headers={'Content-Type': 'application/json'}, body=body)
            response = response.data.decode('UTF-8')
        except Exception as e:
            raise Exception("Unable to create an asset in the dataplane: {e}".format(e=e))
        else:
            if "asset_id" not in response:
                raise Exception("Unable to create an asset in the dataplane: {e}".format(e=response))
            else:
                print("Asset created: {asset}".format(asset=response))
                return json.loads(response)

    def upload_metadata(self, operator_name, results):
        url = self.base_url + 'data/' + self.asset_id
        body = json.dumps({
            "operator_name": operator_name,
            "results": results
        })
        try:
            self.http.request('POST', url, headers={'Content-Type': 'application/json'}, body=body)
        except Exception as e:
            # return the error so we can pass it to our output object
            return {"status": "failed", "message": e}
        else:
            return {"status": "success"}

    def persist_media(self, **kwargs):
        # TODO: Add input checking to ensure kwargs isn't empty
        s3_client = boto3.client("s3")
        # If S3bucket and S3key are included we'll just copy it into the dataplane s3bucket
        try:
            s3bucket = kwargs["s3bucket"]
            s3key = kwargs["s3key"]
        except KeyError:
            print("No s3object included")
            pass
        else:
            new_key = self.base_s3_key + self.asset_id + '/' + 'derived' + '/' + self.workflow_id + '/' + \
                      s3key.split('/')[-1]
            print(new_key)
            print(dataplane_bucket)
            print(s3key)
            print(s3bucket)
            try:
                s3_client.copy_object(
                    Bucket=dataplane_bucket,
                    Key=new_key,
                    CopySource={'Bucket': s3bucket, 'Key': s3key}
                )
            except Exception as e:
                print("Unable to copy the operator created asset to the dataplane bucket:", e)
                return {"status": "failed", "message": e}
            else:
                return {"status": "success", "s3bucket": dataplane_bucket, "s3key": new_key}

        # If no s3bucket or s3key is passed, we will write the object to s3 and return the location
        try:
            data = kwargs["data"]
            file_name = kwargs["file_name"]
        except KeyError as e:
            print("Missing a required input:", e)
            return {"status": "failed", "message": e}
        data = data.encode('utf-8')
        key = self.base_s3_key + self.asset_id + '/' + 'derived' + '/' + self.workflow_id + '/' + file_name

        try:
            s3_client.put_object(Bucket=dataplane_bucket, Key=key, Body=data)
        except Exception as e:
            print("Unable to write data to s3:", e)
            return {"status": "failed", "message": e}
        else:
            return {"status": "success", "s3bucket": dataplane_bucket, "s3key": key}
