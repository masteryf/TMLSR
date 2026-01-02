import os
import oss2
from server.config import settings

class OSSHandler:
    def __init__(self):
        self.config = settings.oss_config
        self.endpoint = self.config.get("endpoint")
        self.access_key_id = self.config.get("access_key_id")
        self.access_key_secret = self.config.get("access_key_secret")
        self.bucket_name = self.config.get("bucket_name")
        
        if self.access_key_id and self.access_key_secret and self.endpoint and self.bucket_name:
            self.auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            self.bucket = oss2.Bucket(self.auth, self.endpoint, self.bucket_name)
        else:
            print("Warning: OSS config missing. OSSHandler disabled.")
            self.bucket = None

    def upload_file(self, local_path, oss_path, progress_callback=None):
        if not self.bucket:
            return False
        
        try:
            self.bucket.put_object_from_file(oss_path, local_path, progress_callback=progress_callback)
            return True
        except Exception as e:
            print(f"OSS upload failed: {e}")
            return False
