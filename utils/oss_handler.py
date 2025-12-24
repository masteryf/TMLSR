import os
import yaml
import oss2
from concurrent.futures import ThreadPoolExecutor

class OSSHandler:
    def __init__(self, config_path='config.yaml'):
        """
        Initialize OSS Handler with configuration from yaml file.
        
        Args:
            config_path (str): Path to config.yaml
        """
        self.config = self._load_config(config_path)
        self.bucket = self._init_bucket()
        
    def _load_config(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config['oss']

    def _init_bucket(self):
        auth = oss2.Auth(self.config['access_key_id'], self.config['access_key_secret'])
        # Ensure endpoint has protocol
        endpoint = self.config['endpoint']
        if not endpoint.startswith('http'):
            endpoint = 'http://' + endpoint
            
        bucket = oss2.Bucket(auth, endpoint, self.config['bucket_name'])
        return bucket

    def upload_file(self, local_path, oss_path, progress_callback=None):
        """
        Upload a single file to OSS.
        
        Args:
            local_path (str): Local file path.
            oss_path (str): Destination path in OSS.
            progress_callback (callable): Function called with (consumed_bytes, total_bytes).
        """
        if not os.path.exists(local_path):
            print(f"File not found: {local_path}")
            return False
            
        print(f"Uploading {local_path} to {oss_path}...")
        try:
            oss2.resumable_upload(
                self.bucket, 
                oss_path, 
                local_path,
                progress_callback=progress_callback
            )
            print(f"Upload success: {oss_path}")
            return True
        except Exception as e:
            print(f"Upload failed: {e}")
            return False

    def download_file(self, oss_path, local_path):
        """
        Download a single file from OSS.
        
        Args:
            oss_path (str): Source path in OSS.
            local_path (str): Destination local path.
        """
        print(f"Downloading {oss_path} to {local_path}...")
        try:
            # Create parent directory if not exists
            os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
            
            oss2.resumable_download(self.bucket, oss_path, local_path)
            print(f"Download success: {local_path}")
            return True
        except Exception as e:
            print(f"Download failed: {e}")
            return False

    def batch_upload(self, file_pairs, max_workers=4):
        """
        Parallel upload multiple files.
        
        Args:
            file_pairs (list): List of (local_path, oss_path) tuples.
            max_workers (int): Number of parallel threads.
        """
        print(f"Starting batch upload for {len(file_pairs)} files...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.upload_file, local, remote)
                for local, remote in file_pairs
            ]
            for future in futures:
                future.result()
        print("Batch upload completed.")

    def batch_download(self, file_pairs, max_workers=4):
        """
        Parallel download multiple files.
        
        Args:
            file_pairs (list): List of (oss_path, local_path) tuples.
            max_workers (int): Number of parallel threads.
        """
        print(f"Starting batch download for {len(file_pairs)} files...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.download_file, remote, local)
                for remote, local in file_pairs
            ]
            for future in futures:
                future.result()
        print("Batch download completed.")
