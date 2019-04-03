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
