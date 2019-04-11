import urllib3
import json
import boto3
import os

base_url = os.environ['dataplane_base_url']
dataplane_bucket = os.environ['dataplane_bucket']
base_s3_key = os.environ['base_s3_key']


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
    def __init__(self, asset_id, workflow_id):
        self.base_url = base_url
        self.http = urllib3.PoolManager()
        self.asset_id = asset_id
        self.s3_client = boto3.client("s3")
        self.base_s3_key = base_s3_key
        self.workflow_id = workflow_id

    def upload_metadata(self, operator_name, results):
        url = self.base_url + self.asset_id
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
        try:
            s3bucket = kwargs["s3bucket"]
            s3key = kwargs["s3key"]
        except KeyError:
            print("No s3object included")
            pass
        else:
            new_key = self.base_s3_key + self.asset_id + '/' + 'derived' + '/' + self.workflow_id + '/' + s3key.split('/')[-1]
            try:
                self.s3_client.copy_object(
                    Bucket=dataplane_bucket,
                    Key=new_key,
                    CopySource={'Bucket': s3bucket, 'Key': s3key}
                )
            except Exception as e:
                print("Unable to copy the operator created asset to the dataplane bucket:", e)
                return {"status": "failed", "message": e}
            else:
                return {"status": "success", "s3bucket": dataplane_bucket, "s3key": new_key}
        try:
            data = kwargs["data"]
            file_name = kwargs["file_name"]
        except KeyError as e:
            print("Missing a required input:", e)
            return {"status": "failed", "message": e}
        data = data.encode('utf-8')
        key = self.base_s3_key + self.asset_id + '/' + 'derived' + '/' + self.workflow_id + '/' + file_name

        try:
            self.s3_client.put_object(Bucket=dataplane_bucket, Key=key, Body=data)
        except Exception as e:
            print("Unable to write data to s3:", e)
            return {"status": "failed", "message": e}
        else:
            return {"status": "success", "s3bucket": dataplane_bucket, "s3key": key}
