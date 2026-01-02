import os
import queue
import time
import threading
from typing import List, Tuple, Dict, Optional
from .comfy_utils import run_workflow_task

class ComfyAPIPool:
    def __init__(self, servers: List[str]):
        """
        Initialize the API pool with a list of server addresses.
        Each server is added to a thread-safe queue for load balancing.
        """
        self.servers = servers
        self.server_queue = queue.Queue()
        for server in servers:
            self.server_queue.put(server)
        
        # Monitor server status
        self.server_status: Dict[str, Dict] = {
            s: {"status": "idle", "task_id": None, "last_active": None} 
            for s in servers
        }
        self.lock = threading.Lock()

    def get_status(self) -> List[Dict]:
        """Return the current status of all servers."""
        with self.lock:
            # Create a list of status objects
            return [
                {"address": addr, **info}
                for addr, info in self.server_status.items()
            ]

    def process_task(self, workflow_path: str, input_path: str, output_dir: str, task_id: Optional[str] = None) -> List[str]:
        """
        Process a single task using an available server from the pool.
        
        Args:
            workflow_path (str): Path to the workflow JSON file.
            input_path (str): Path to the input file (image/video).
            output_dir (str): Directory to save outputs.
            task_id (str, optional): Task ID for monitoring purposes.
            
        Returns:
            List[str]: List of output file paths.
        """
        # 1. Acquire a server (blocks until one is available)
        server = self.server_queue.get()
        print(f"[Pool] Assigned task {task_id or 'unknown'} ({os.path.basename(input_path)}) to server {server}")
        
        # Update status to busy
        with self.lock:
            self.server_status[server] = {
                "status": "busy",
                "task_id": task_id,
                "last_active": time.time()
            }

        try:
            # 2. Execute the workflow using the utility function
            # run_workflow_task handles connection, upload, execution, and download
            return run_workflow_task(server, workflow_path, input_path, output_dir)
            
        except Exception as e:
            print(f"[Pool] Error processing task on {server}: {e}")
            raise e
            
        finally:
            # Update status to idle
            with self.lock:
                self.server_status[server] = {
                    "status": "idle",
                    "task_id": None,
                    "last_active": time.time()
                }

            # 3. Release the server back to the pool
            self.server_queue.put(server)
            # print(f"[Pool] Server {server} released.")
