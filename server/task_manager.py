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
from utils import OSSHandler
from utils.comfy_pool import ComfyAPIPool

class TaskManager:
    def __init__(self):
        self.tasks = {} # In-memory storage: task_id -> dict
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        
        # Use server count as concurrency limit as requested
        self.max_workers = len(settings.comfyui_servers)
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        self.oss_handler = OSSHandler()
        self.comfy_pool = ComfyAPIPool(settings.comfyui_servers)
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        self._cleanup_stale_files()
        
        print(f"TaskManager initialized with {self.max_workers} concurrent workers.")

    def _cleanup_stale_files(self):
        """Clean up stale temporary files from previous runs."""
        print("Cleaning up stale temporary files...")
        
        # 1. Clean temp_tasks directory
        if os.path.exists("temp_tasks"):
            try:
                shutil.rmtree("temp_tasks")
                print("Removed stale 'temp_tasks' directory.")
            except Exception as e:
                print(f"Failed to remove 'temp_tasks': {e}")
                
        # 2. Clean VideoSRProcessor temp directories (temp_*)
        # Look for directories matching temp_* in the current directory
        # Be careful not to delete other temp folders if any
        import glob
        for temp_dir in glob.glob("temp_*"):
            if os.path.isdir(temp_dir):
                # Double check it looks like one of our temp dirs
                # VideoSRProcessor: temp_{video_name}_{timestamp}
                # We can just delete anything starting with temp_ that is a directory, 
                # assuming we don't have other important folders starting with temp_
                try:
                    shutil.rmtree(temp_dir)
                    print(f"Removed stale directory: {temp_dir}")
                except Exception as e:
                    print(f"Failed to remove '{temp_dir}': {e}")

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
                "pool_status": self.comfy_pool.get_status(),
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
                # Submit task to thread pool for concurrent execution
                self.executor.submit(self._run_task_async, task_id)
            except Exception as e:
                print(f"Worker loop error: {e}")

    def _run_task_async(self, task_id):
        """Wrapper to run task and mark queue item as done."""
        try:
            self._process_task_wrapper(task_id)
        except Exception as e:
            print(f"Async task execution error for {task_id}: {e}")
        finally:
            self.queue.task_done()

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

    def _update_stage(self, task_id, stage_name, status, duration=0.0, progress=None, detail=None):
        # Round duration to 2 decimal places for cleaner output
        duration = round(duration, 2)
        
        with self.lock:
            task = self.tasks[task_id]
            # Check if stage exists, update it, or append
            found = False
            for stage in task["stages"]:
                if stage["name"] == stage_name:
                    stage["status"] = status
                    if duration > 0:
                        stage["duration"] = duration
                    if progress is not None:
                        stage["progress"] = progress
                    if detail is not None:
                        stage["detail"] = detail
                    found = True
                    break
            if not found:
                task["stages"].append({
                    "name": stage_name,
                    "status": status,
                    "duration": duration,
                    "progress": progress if progress is not None else 0,
                    "detail": detail if detail else ""
                })

    def _execute_task(self, task_id):
        task = self.tasks[task_id]
        params = task["params"]
        temp_dir = task["temp_dir"]
        os.makedirs(temp_dir, exist_ok=True)
        
        input_url = str(params["url"])
        
        # Determine Workflow Name
        workflow_name = params.get("workflow")
        model_name = params.get("model")
        
        if not workflow_name:
            if model_name:
                if "seedvr2" in model_name.lower():
                    workflow_name = "SeedVR2Defeat"
                else:
                    workflow_name = "ESRGANDefeat"
            else:
                 workflow_name = "ESRGANDefeat" # Default
                 
        workflow_path = os.path.join(os.getcwd(), "workflows", f"{workflow_name}.json")
        if not os.path.exists(workflow_path):
             # Fallback check
             if os.path.exists(os.path.join(os.getcwd(), "workflows", f"{workflow_name}")):
                 workflow_path = os.path.join(os.getcwd(), "workflows", f"{workflow_name}")
             else:
                 raise FileNotFoundError(f"Workflow file not found: {workflow_name}")

        try:
            # 1. Download
            start_time = time.time()
            self._update_stage(task_id, "download", "running", progress=0, detail="Starting download...")
            
            # Use extension from url or default based on type
            ext = os.path.splitext(input_url.split("?")[0])[1]
            if not ext:
                ext = ".mp4" if params.get("type") == TaskType.VIDEO else ".png"
            
            # Use original filename to avoid potential conflicts or node validation issues
            original_basename = os.path.basename(input_url.split("?")[0])
            if not original_basename or len(original_basename) > 200: # Basic safety
                 local_input_filename = f"input{ext}"
            else:
                 local_input_filename = original_basename

            local_input = os.path.join(temp_dir, local_input_filename)
            
            print(f"Downloading {input_url} to {local_input}...")
            
            def download_progress(current, total):
                if total > 0:
                    pct = round((current / total) * 100, 1)
                    self._update_stage(task_id, "download", "running", progress=pct, detail=f"{round(current/1024/1024, 1)}MB / {round(total/1024/1024, 1)}MB")

            self._download_file(input_url, local_input, progress_callback=download_progress)
            self._update_stage(task_id, "download", "success", duration=time.time() - start_time, progress=100, detail="Download complete")
            
            # 2. Process
            start_time = time.time()
            self._update_stage(task_id, "process", "running", progress=0, detail=f"Processing with {workflow_name}...")
            
            output_paths = self.comfy_pool.process_task(workflow_path, local_input, temp_dir, task_id=task_id)
            
            if not output_paths:
                raise RuntimeError("Workflow produced no output files")
            
            local_output = output_paths[0] # Take the first output
            local_output_filename = os.path.basename(local_output)

            self._update_stage(task_id, "process", "success", duration=time.time() - start_time, progress=100, detail="Processing complete")
            
            # 3. Upload
            start_time = time.time()
            self._update_stage(task_id, "upload", "running", progress=0, detail="Starting upload...")
            
            oss_filename = f"outputs/{task_id}/{local_output_filename}"
            
            def upload_progress(consumed, total):
                if total > 0:
                    pct = round((consumed / total) * 100, 1)
                    self._update_stage(task_id, "upload", "running", progress=pct, detail=f"{round(consumed/1024/1024, 1)}MB / {round(total/1024/1024, 1)}MB")

            success = self.oss_handler.upload_file(local_output, oss_filename, progress_callback=upload_progress)
            if not success:
                raise RuntimeError("Failed to upload to OSS")
                
            # Construct OSS URL
            bucket_name = self.oss_handler.config['bucket_name']
            endpoint = self.oss_handler.config['endpoint']
            if not endpoint.startswith("http"):
                endpoint = "https://" + endpoint
            ep_host = endpoint.split("://")[-1]
            output_url = f"https://{bucket_name}.{ep_host}/{oss_filename}"
            
            file_size = os.path.getsize(local_output) / (1024 * 1024) # MB
            
            with self.lock:
                self.tasks[task_id]["output"] = {
                    "url": output_url,
                    "size_mb": round(file_size, 2)
                }
            
            self._update_stage(task_id, "upload", "success", duration=time.time() - start_time, progress=100, detail="Upload complete")

        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


    def _download_file(self, url, local_path, progress_callback=None):
        if url.startswith("http"):
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            with requests.get(url, stream=True, headers=headers) as r:
                r.raise_for_status()
                total_length = r.headers.get('content-length')
                
                with open(local_path, 'wb') as f:
                    if total_length is None: # no content length header
                        f.write(r.content)
                        if progress_callback:
                            progress_callback(1, 1) # Just say done
                    else:
                        dl = 0
                        total_length = int(total_length)
                        for chunk in r.iter_content(chunk_size=8192):
                            dl += len(chunk)
                            f.write(chunk)
                            if progress_callback:
                                progress_callback(dl, total_length)
                                
        elif url.startswith("file://"):
            src_path = url[7:]
            if os.path.exists(src_path):
                # Fake progress for local copy
                if progress_callback:
                    size = os.path.getsize(src_path)
                    progress_callback(0, size)
                shutil.copy2(src_path, local_path)
                if progress_callback:
                    size = os.path.getsize(src_path)
                    progress_callback(size, size)
            else:
                raise FileNotFoundError(f"Local file not found: {src_path}")
        else:
            # Assume it's a local path if it exists
            if os.path.exists(url):
                if progress_callback:
                    size = os.path.getsize(url)
                    progress_callback(0, size)
                shutil.copy2(url, local_path)
                if progress_callback:
                    size = os.path.getsize(url)
                    progress_callback(size, size)
            else:
                raise ValueError(f"Unsupported URL scheme or file not found: {url}")

task_manager = TaskManager()
