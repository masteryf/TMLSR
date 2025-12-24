import os
import time
import uuid
import threading
import traceback
import requests
import queue
import shutil
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from .models import TaskCreateRequest, TaskResponse, TaskStatus, TaskStage, TaskOutput, TaskType
from .config import settings
from utils import ImageSRProcessor, VideoSRProcessor, OSSHandler

class TaskManager:
    def __init__(self):
        self.tasks = {} # In-memory storage: task_id -> dict
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        
        # Initialize processors lazily or globally?
        # To support concurrency, we might need a pool of processors or rely on the processor's internal handling.
        # Since SR is GPU heavy, we should limit the number of concurrent SR tasks.
        self.max_workers = settings.max_workers
        self.semaphore = threading.Semaphore(self.max_workers)
        
        self.oss_handler = OSSHandler()
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        print(f"TaskManager initialized with {self.max_workers} concurrent workers.")

    def create_task(self, request: TaskCreateRequest) -> str:
        task_id = str(uuid.uuid4()).replace('-', '')
        now = datetime.utcnow().isoformat() + "Z"
        
        task_data = {
            "task_id": task_id,
            "status": TaskStatus.PENDING,
            "created_at": now,
            "updated_at": now,
            "params": request.model_dump(),
            "stages": [],
            "output": None,
            "error": None,
            "retries": 0,
            "temp_dir": os.path.join("temp_tasks", task_id)
        }
        
        with self.lock:
            self.tasks[task_id] = task_data
            
        self.queue.put(task_id)
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskResponse]:
        with self.lock:
            data = self.tasks.get(task_id)
            if not data:
                return None
            return TaskResponse(**data)

    def get_monitor_stats(self):
        with self.lock:
            total_tasks = len(self.tasks)
            status_counts = {
                TaskStatus.PENDING: 0,
                TaskStatus.PROCESSING: 0,
                TaskStatus.COMPLETED: 0,
                TaskStatus.FAILED: 0,
                TaskStatus.CANCELED: 0
            }
            
            # Sort tasks by created_at desc
            sorted_tasks = sorted(
                self.tasks.values(), 
                key=lambda x: x.get("created_at", ""), 
                reverse=True
            )
            
            for task in sorted_tasks:
                s = task.get("status")
                if s in status_counts:
                    status_counts[s] += 1
            
            # Return top 50 recent tasks for dashboard
            recent_tasks = sorted_tasks[:50]
            
            return {
                "system": {
                    "max_workers": self.max_workers,
                    "active_workers": status_counts[TaskStatus.PROCESSING], # Approximation
                    "queue_size": self.queue.qsize()
                },
                "stats": status_counts,
                "tasks": recent_tasks
            }

    def cancel_task(self, task_id: str) -> bool:
        with self.lock:
            if task_id not in self.tasks:
                return False
            task = self.tasks[task_id]
            if task["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED]:
                return False
            
            task["status"] = TaskStatus.CANCELED
            task["updated_at"] = datetime.utcnow().isoformat() + "Z"
            # Note: This doesn't stop a running thread immediately, 
            # but the worker loop checks status before processing.
            return True

    def _worker_loop(self):
        while True:
            try:
                task_id = self.queue.get()
                self._process_task_wrapper(task_id)
                self.queue.task_done()
            except Exception as e:
                print(f"Worker loop error: {e}")

    def _process_task_wrapper(self, task_id):
        # Check if canceled
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or task["status"] == TaskStatus.CANCELED:
                return

            task["status"] = TaskStatus.PROCESSING
            task["updated_at"] = datetime.utcnow().isoformat() + "Z"

        try:
            self._execute_task(task_id)
            with self.lock:
                self.tasks[task_id]["status"] = TaskStatus.COMPLETED
                self.tasks[task_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        except Exception as e:
                print(f"Task {task_id} failed: {e}")
                traceback.print_exc()
                
                with self.lock:
                    task = self.tasks[task_id]
                    task["retries"] += 1
                    if task["retries"] <= settings.max_retries:
                        print(f"Retrying task {task_id} ({task['retries']}/{settings.max_retries})...")
                        task["status"] = TaskStatus.PENDING # Reset to pending
                        task["error"] = f"Retry {task['retries']}: {str(e)}"
                        # Re-queue after delay (blocking this thread briefly is okay if we have enough workers, 
                        # but ideally use a scheduled executor. For simplicity, just push back.)
                        self.queue.put(task_id)
                    else:
                        task["status"] = TaskStatus.FAILED
                        task["error"] = str(e)
                        task["updated_at"] = datetime.utcnow().isoformat() + "Z"

    def _update_stage(self, task_id, stage_name, status, duration=0.0):
        with self.lock:
            task = self.tasks[task_id]
            # Check if stage exists, update it, or append
            found = False
            for stage in task["stages"]:
                if stage["name"] == stage_name:
                    stage["status"] = status
                    stage["duration"] = duration
                    found = True
                    break
            if not found:
                task["stages"].append({
                    "name": stage_name,
                    "status": status,
                    "duration": duration
                })

    def _execute_task(self, task_id):
        task = self.tasks[task_id]
        params = task["params"]
        temp_dir = task["temp_dir"]
        os.makedirs(temp_dir, exist_ok=True)
        
        input_url = str(params["url"])
        task_type = params.get("type", TaskType.VIDEO)
        
        try:
            # 1. Download
            start_time = time.time()
            local_input_filename = "input_video.mp4" if task_type == TaskType.VIDEO else "input_image.png"
            local_input = os.path.join(temp_dir, local_input_filename)
            
            print(f"Downloading {input_url} to {local_input}...")
            self._download_file(input_url, local_input)
            self._update_stage(task_id, "download", "success", time.time() - start_time)
            
            # 2. Process
            start_time = time.time()
            local_output_filename = "output_video.mp4" if task_type == TaskType.VIDEO else "output_image.png"
            local_output = os.path.join(temp_dir, local_output_filename)
            
            outscale = params.get("outscale")
            output_magnification = params.get("output_magnification")
            gpu_id = params.get("gpu_id", 0)

            processor = None
            if task_type == TaskType.VIDEO:
                processor = VideoSRProcessor(gpu_id=gpu_id, scale=4) # Default scale 4, overridden by outscale
                processor.process_video(
                    input_path=local_input,
                    output_path=local_output,
                    outscale=outscale,
                    output_magnification=output_magnification,
                    keep_audio=params.get("audio", True)
                )
            else:
                processor = ImageSRProcessor(gpu_id=gpu_id, scale=4)
                # Parse output_dims from magnification if needed, but processor handles it if we pass magnification logic
                # Wait, ImageSRProcessor takes output_dims (w, h). 
                # We need to calculate it if output_magnification is provided.
                
                dims = None
                if output_magnification:
                    img = requests.get(input_url, stream=True).raw # Or read local
                    # Actually we have local file now
                    import cv2
                    img_mat = cv2.imread(local_input)
                    if img_mat is None:
                        raise ValueError("Invalid image file")
                    h, w = img_mat.shape[:2]
                    dims = (int(w * output_magnification), int(h * output_magnification))
                
                processor.process_image(
                    img_input=local_input,
                    output_path=local_output,
                    outscale=outscale,
                    output_dims=dims
                )
            
            # Explicit cleanup after processing
            if processor:
                processor.cleanup()

            self._update_stage(task_id, "process", "success", time.time() - start_time)
            
            # 3. Upload
            start_time = time.time()
            oss_filename = f"outputs/{task_id}/{local_output_filename}"
            
            success = self.oss_handler.upload_file(local_output, oss_filename)
            if not success:
                raise RuntimeError("Failed to upload to OSS")
                
            # Construct OSS URL (Assuming public read or we need to generate signed url)
            # For now, return the oss path or a constructed URL if endpoint is known
            bucket_name = self.oss_handler.config['bucket_name']
            endpoint = self.oss_handler.config['endpoint']
            # Basic URL construction (works for public buckets)
            # If private, we might need a signed URL, but let's assume standard access for now
            # or return the path so client can sign it.
            # The demo output showed: "https://oss-bucket/path/to/output.mp4"
            
            # Let's try to construct a valid URL
            if not endpoint.startswith("http"):
                endpoint = "https://" + endpoint
            
            # format: https://bucket.endpoint/object
            # cleanup endpoint if it contains protocol
            ep_host = endpoint.split("://")[-1]
            output_url = f"https://{bucket_name}.{ep_host}/{oss_filename}"
            
            file_size = os.path.getsize(local_output) / (1024 * 1024) # MB
            
            with self.lock:
                self.tasks[task_id]["output"] = {
                    "url": output_url,
                    "size_mb": round(file_size, 2)
                }
            
            self._update_stage(task_id, "upload", "success", time.time() - start_time)

        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def _download_file(self, url, local_path):
        if url.startswith("http"):
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        elif url.startswith("file://"):
            src_path = url[7:]
            if os.path.exists(src_path):
                shutil.copy2(src_path, local_path)
            else:
                raise FileNotFoundError(f"Local file not found: {src_path}")
        else:
            # Assume it's a local path if it exists
            if os.path.exists(url):
                shutil.copy2(url, local_path)
            else:
                raise ValueError(f"Unsupported URL scheme or file not found: {url}")

task_manager = TaskManager()
