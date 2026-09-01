import os
from datetime import timedelta


class AlbumStorage:
    """Adaptador para un bucket GCS privado; la base guarda claves, no URLs."""
    def __init__(self):
        from google.cloud import storage
        bucket_name = os.environ.get("BUCKET_NAME")
        if not bucket_name:
            raise RuntimeError("BUCKET_NAME is not configured")
        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("BUCKET_GOOGLE_CREDENTIAL")
        if credentials_path:
            self.client = storage.Client.from_service_account_json(credentials_path)
        else:
            self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def upload(self, key, stream, mime_type):
        self.bucket.blob(key).upload_from_file(stream, content_type=mime_type, rewind=True, if_generation_match=0)

    def delete(self, key):
        if key:
            self.bucket.blob(key).delete(if_generation_match=None)

    def signed_url(self, key):
        return self.bucket.blob(key).generate_signed_url(version="v4", expiration=timedelta(minutes=15), method="GET")
