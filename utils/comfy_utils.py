import websocket
import uuid
import json
import requests
import os
import time
from typing import Dict, List, Union, Any, Optional

class ComfyUIClient:
    def __init__(self, server_address="127.0.0.1:8000"):
        server_address = server_address.rstrip('/')
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.ws = None
        
        # Handle scheme in server_address
        if server_address.startswith("http://"):
            host = server_address.replace("http://", "")
            self.http_base = server_address
            self.ws_url = f"ws://{host}/ws?clientId={self.client_id}"
        elif server_address.startswith("https://"):
            host = server_address.replace("https://", "")
            self.http_base = server_address
            self.ws_url = f"wss://{host}/ws?clientId={self.client_id}"
        else:
            # Default to http/ws
            self.http_base = f"http://{server_address}"
            self.ws_url = f"ws://{server_address}/ws?clientId={self.client_id}"

    def connect(self):
        """Connect to the WebSocket server."""
        self.ws = websocket.WebSocket()
        self.ws.connect(self.ws_url)

    def close(self):
        if self.ws:
            self.ws.close()

    def upload_image(self, file_path: str, subfolder: str = "", overwrite: bool = False, image_type: str = "input") -> Dict:
        """
        Upload an image to ComfyUI.
        """
        url = f"{self.http_base}/upload/image"
        filename = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            files = {'image': (filename, f)}
            data = {
                'subfolder': subfolder,
                'overwrite': 'true' if overwrite else 'false',
                'type': image_type
            }
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            return response.json()

    def queue_prompt(self, prompt: Dict) -> str:
        """
        Queue a workflow (API format prompt).
        Returns the prompt_id.
        """
        p = {"prompt": prompt, "client_id": self.client_id}
        url = f"{self.http_base}/prompt"
        response = requests.post(url, json=p)
        response.raise_for_status()
        try:
            return response.json()['prompt_id']
        except KeyError:
            print(f"Failed to get prompt_id. Response: {response.text}")
            raise

    def get_history(self, prompt_id: str) -> Dict:
        url = f"{self.http_base}/history/{prompt_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def get_image(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url = f"{self.http_base}/view"
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.content

    def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> Dict:
        """
        Wait for the prompt to complete via WebSocket.
        Returns the output data (including image filenames).
        """
        if not self.ws:
            self.connect()
        
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError("Workflow execution timed out")
            
            try:
                out = self.ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executing':
                        data = message['data']
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            # Execution finished
                            break
            except Exception as e:
                # Handle connection issues or reconnect if needed
                raise e
        
        # Get history to retrieve outputs
        history = self.get_history(prompt_id)
        if prompt_id in history:
            return history[prompt_id]
        return {}

class WorkflowConverter:
    @staticmethod
    def convert_ui_to_api(workflow_ui_json: Dict) -> Dict:
        """
        Convert a ComfyUI Workflow JSON (UI format) to API Prompt format.
        This is a best-effort converter tailored for common nodes and the user's specific workflows.
        """
        prompt = {}
        nodes = workflow_ui_json.get("nodes", [])
        
        # Create a lookup for links: Link ID -> (Node ID, Slot Index)
        links_lookup = {}
        for node in nodes:
            outputs = node.get("outputs", [])
            for slot_idx, output in enumerate(outputs):
                if output.get("links"):
                    for link_id in output["links"]:
                        links_lookup[link_id] = (str(node["id"]), slot_idx)
        
        for node in nodes:
            node_id = str(node["id"])
            class_type = node["type"]
            inputs = {}
            
            # 1. Map Linked Inputs
            node_inputs_def = node.get("inputs", [])
            for input_def in node_inputs_def:
                link_id = input_def.get("link")
                if link_id is not None and link_id in links_lookup:
                    inputs[input_def["name"]] = links_lookup[link_id]
            
            # 2. Map Widget Values
            widgets_values = node.get("widgets_values", [])
            widget_defs = [i for i in node_inputs_def if "widget" in i]
            
            w_idx = 0
            v_idx = 0
            
            while w_idx < len(widget_defs) and v_idx < len(widgets_values):
                w_def = widget_defs[w_idx]
                w_name = w_def["name"]
                
                # Assign value
                inputs[w_name] = widgets_values[v_idx]
                
                # Check for seed/noise_seed to skip control_after_generate
                if w_name in ["seed", "noise_seed"]:
                    v_idx += 2 # Skip value and control
                else:
                    v_idx += 1
                
                w_idx += 1
            
            prompt[node_id] = {
                "class_type": class_type,
                "inputs": inputs
            }
            
        return prompt

class NGSRWorkflow:
    def __init__(self, workflow_path: str, client: Optional[ComfyUIClient] = None):
        with open(workflow_path, 'r', encoding='utf-8') as f:
            self.workflow_ui = json.load(f)
        
        self.prompt = WorkflowConverter.convert_ui_to_api(self.workflow_ui)
        self.client = client
        
        # Identify key nodes
        self.load_image_node_id = self._find_node_id_by_type("LoadImage")
        self.load_video_node_id = self._find_node_id_by_type("VHS_LoadVideo") or self._find_node_id_by_type("LoadVideo")
        self.seed_node_id = self._find_node_id_by_type("SeedVR2VideoUpscaler") or self._find_node_id_by_type("KSampler") 

    def _find_node_id_by_type(self, type_name: str) -> Optional[str]:
        for node_id, node_data in self.prompt.items():
            if node_data["class_type"] == type_name:
                return node_id
        return None

    def set_input(self, filename: str):
        # Try setting image first
        if self.load_image_node_id:
            if "image" in self.prompt[self.load_image_node_id]["inputs"]:
                 self.prompt[self.load_image_node_id]["inputs"]["image"] = filename
        
        # Try setting video
        if self.load_video_node_id:
            if "video" in self.prompt[self.load_video_node_id]["inputs"]:
                self.prompt[self.load_video_node_id]["inputs"]["video"] = filename
            elif "file" in self.prompt[self.load_video_node_id]["inputs"]:
                 self.prompt[self.load_video_node_id]["inputs"]["file"] = filename
            elif "upload" in self.prompt[self.load_video_node_id]["inputs"]:
                 self.prompt[self.load_video_node_id]["inputs"]["upload"] = filename

    def set_seed(self, seed: int):
        if self.seed_node_id:
            if "seed" in self.prompt[self.seed_node_id]["inputs"]:
                self.prompt[self.seed_node_id]["inputs"]["seed"] = seed
            elif "noise_seed" in self.prompt[self.seed_node_id]["inputs"]:
                self.prompt[self.seed_node_id]["inputs"]["noise_seed"] = seed

    def run(self, input_path: str, output_dir: str = "./output") -> List[str]:
        """
        Run the workflow for a local input file (image/video).
        Uploads input -> Runs -> Downloads result.
        Returns list of output file paths.
        """
        if not self.client:
            raise ValueError("Client not initialized")

        # 1. Upload Input
        # Use overwrite=True to ensure we are using the file we just uploaded
        upload_resp = self.client.upload_image(input_path, overwrite=True)
        filename = upload_resp["name"]
        
        # 2. Update Workflow
        self.set_input(filename)
        
        # 3. Queue
        prompt_id = self.client.queue_prompt(self.prompt)
        
        # 4. Wait
        result = self.client.wait_for_completion(prompt_id)
        
        # 5. Download Outputs
        output_files = []
        if 'outputs' in result:
            for node_id, node_output in result['outputs'].items():
                # Handle Images
                if 'images' in node_output:
                    for img in node_output['images']:
                        img_data = self.client.get_image(img['filename'], img['subfolder'], img['type'])
                        
                        os.makedirs(output_dir, exist_ok=True)
                        out_name = f"{img['filename']}"
                        out_path = os.path.join(output_dir, out_name)
                        
                        with open(out_path, 'wb') as f:
                            f.write(img_data)
                        output_files.append(out_path)
                
                # Handle GIFs/Videos (VHS_VideoCombine often returns gifs or filenames in different keys)
                if 'gifs' in node_output:
                    for gif in node_output['gifs']:
                        img_data = self.client.get_image(gif['filename'], gif['subfolder'], gif['type'])
                        
                        os.makedirs(output_dir, exist_ok=True)
                        out_name = f"{gif['filename']}"
                        out_path = os.path.join(output_dir, out_name)
                        
                        with open(out_path, 'wb') as f:
                            f.write(img_data)
                        output_files.append(out_path)

                if 'videos' in node_output:
                    for video in node_output['videos']:
                        img_data = self.client.get_image(video['filename'], video['subfolder'], video['type'])
                        
                        os.makedirs(output_dir, exist_ok=True)
                        out_name = f"{video['filename']}"
                        out_path = os.path.join(output_dir, out_name)
                        
                        with open(out_path, 'wb') as f:
                            f.write(img_data)
                        output_files.append(out_path)

        return output_files

def run_workflow_task(server_address: str, workflow_path: str, input_path: str, output_dir: str):
    """
    Helper for parallel execution.
    """
    client = ComfyUIClient(server_address)
    try:
        client.connect()
        wf = NGSRWorkflow(workflow_path, client)
        return wf.run(input_path, output_dir)
    finally:
        client.close()
