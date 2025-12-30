import json
import urllib.request
import urllib.parse
import urllib.error
import time
import os
import mimetypes
import uuid

class ComfyUIClient:
    def __init__(self, server_address="127.0.0.1:8188"):
        # Allow specifying protocol, otherwise default to http
        if server_address.startswith("http://") or server_address.startswith("https://"):
            self.base_url = server_address
        else:
            self.base_url = f"http://{server_address}"
        
        # Remove trailing slash if present
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]
            
        self.object_info = None
        self.client_id = str(uuid.uuid4())

    def check_health(self):
        try:
            with urllib.request.urlopen(f"{self.base_url}/system_stats", timeout=2) as response:
                return response.status == 200
        except:
            return False

    def get_object_info(self):
        if self.object_info is None:
            try:
                with urllib.request.urlopen(f"{self.base_url}/object_info") as response:
                    self.object_info = json.loads(response.read())
            except Exception as e:
                print(f"Failed to get object_info: {e}")
                raise
        return self.object_info

    def upload_image(self, image_path, subfolder="", overwrite=False):
        """Uploads an image to ComfyUI."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        with open(image_path, "rb") as f:
            file_data = f.read()
            
        filename = os.path.basename(image_path)
        
        # Prepare multipart upload manually using standard lib is painful, 
        # so we will use a simpler approach if possible, or construct the body carefully.
        boundary = '----WebKitFormBoundary' + uuid.uuid4().hex
        
        body = []
        # Image field
        body.append(f'--{boundary}'.encode())
        content_type = mimetypes.guess_type(image_path)[0] or 'application/octet-stream'
        body.append(f'Content-Disposition: form-data; name="image"; filename="{filename}"'.encode())
        body.append(f'Content-Type: {content_type}'.encode())
        body.append(b'')
        body.append(file_data)
        
        # Overwrite field
        if overwrite:
            body.append(f'--{boundary}'.encode())
            body.append(b'Content-Disposition: form-data; name="overwrite"')
            body.append(b'')
            body.append(b'true')
            
        # Subfolder field
        if subfolder:
            body.append(f'--{boundary}'.encode())
            body.append(b'Content-Disposition: form-data; name="subfolder"')
            body.append(b'')
            body.append(subfolder.encode())
            
        body.append(f'--{boundary}--'.encode())
        body.append(b'')
        
        data = b'\r\n'.join(body)
        headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}
        
        req = urllib.request.Request(f"{self.base_url}/upload/image", data=data, headers=headers)
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            
        return result

    def queue_prompt(self, prompt, client_id=None, api_key=None):
        p = {"prompt": prompt}
        if client_id:
            p["client_id"] = client_id
        if api_key:
            # Match the user's structure exactly
            p["extra_data"] = {"api_key_comfy_org": api_key}
            
        data = json.dumps(p).encode('utf-8')
        # Use urllib.request directly as in user's example (simpler, no headers needed for this call)
        req = urllib.request.Request(f"{self.base_url}/prompt", data=data)
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            print(f"Error response: {e.read().decode()}")
            raise Exception(f"HTTP Error {e.code}: {e.reason}")

    def get_history(self, prompt_id):
        with urllib.request.urlopen(f"{self.base_url}/history/{prompt_id}") as response:
            return json.loads(response.read())

    def get_image(self, filename, subfolder="", type="output"):
        data = {"filename": filename, "subfolder": subfolder, "type": type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"{self.base_url}/view?{url_values}") as response:
            return response.read()

    def convert_ui_to_api(self, ui_json):
        """Converts a UI-format workflow JSON to API-format prompt JSON."""
        self.get_object_info()
        
        prompt = {}
        
        # Create link map: link_id -> [source_node_id, source_output_slot_index]
        link_map = {}
        for link in ui_json.get('links', []):
            # link format: [id, source_id, source_slot, target_id, target_slot, type]
            link_id = link[0]
            source_id = link[1]
            source_slot = link[2]
            link_map[link_id] = [str(source_id), int(source_slot)]
            
        for node in ui_json.get('nodes', []):
            node_id = str(node['id'])
            class_type = node['type']
            
            # Skip nodes that don't exist in object_info (e.g. Note nodes, or missing custom nodes)
            if class_type not in self.object_info:
                print(f"Warning: Node type '{class_type}' not found in object_info. Skipping node {node_id}.")
                continue
                
            node_info = self.object_info[class_type]
            inputs = {}
            
            # Map widgets values to inputs
            widgets_values = node.get('widgets_values', [])
            config_inputs = node.get('inputs', [])
            
            # Check if we can rely on config_inputs for widget mapping (look for 'widget' key)
            has_widget_info = any('widget' in inp for inp in config_inputs)
            
            if has_widget_info:
                # Use config_inputs to map widgets_values
                widget_idx = 0
                for inp in config_inputs:
                    name = inp['name']
                    # Map widget value
                    if 'widget' in inp and widget_idx < len(widgets_values):
                        inputs[name] = widgets_values[widget_idx]
                        widget_idx += 1
                    
                    # Map link (overrides widget value)
                    link_id = inp.get('link')
                    if link_id is not None and link_id in link_map:
                        inputs[name] = link_map[link_id]
            else:
                # Fallback to object_info logic
                input_order = []
                
                # Prefer 'input_order' if available (newer ComfyUI versions)
                if 'input_order' in node_info and isinstance(node_info['input_order'], dict):
                    # input_order is usually a dict with 'required' and 'optional' lists
                    if 'required' in node_info['input_order']:
                        for name in node_info['input_order']['required']:
                            if name in node_info['input']['required']:
                                input_order.append((name, node_info['input']['required'][name]))
                    if 'optional' in node_info['input_order']:
                        for name in node_info['input_order']['optional']:
                            if 'optional' in node_info['input'] and name in node_info['input']['optional']:
                                 input_order.append((name, node_info['input']['optional'][name]))
                else:
                    # Fallback to old behavior (potentially unreliable order)
                    if 'required' in node_info['input']:
                        for name, config in node_info['input']['required'].items():
                            input_order.append((name, config))
                    if 'optional' in node_info['input']:
                        for name, config in node_info['input']['optional'].items():
                            input_order.append((name, config))
                
                widget_idx = 0
                for name, config in input_order:
                    type_name = config[0]
                    # Heuristic: If type is a list (COMBO) or standard primitive, it's a widget.
                    # If it's a connection type (usually capitalized like IMAGE, MODEL), it's not a widget,
                    # UNLESS it is mapped to a widget in some cases (like LoadImage upload).
                    # But in API format, even widgets are "inputs".
                    
                    is_widget = True
                    if isinstance(type_name, list):
                        is_widget = True
                    elif type_name in ["INT", "FLOAT", "STRING", "BOOLEAN"]:
                        is_widget = True
                    else:
                        # Likely a connection point (IMAGE, MODEL, etc)
                        is_widget = False
                    
                    # Special handling for LoadImage: 'upload' is 'IMAGEUPLOAD' but consumes a widget value?
                    if class_type == 'LoadImage' and name == 'upload':
                         is_widget = True
                    
                    # If it's a widget, take value from widgets_values
                    if is_widget and widget_idx < len(widgets_values):
                        inputs[name] = widgets_values[widget_idx]
                        widget_idx += 1
                
                # Handle connections (override widgets if linked)
                if 'inputs' in node:
                    for inp in node['inputs']:
                        name = inp['name']
                        link_id = inp['link']
                        if link_id is not None and link_id in link_map:
                            inputs[name] = link_map[link_id]
            
            prompt[node_id] = {
                "inputs": inputs,
                "class_type": class_type
            }
            
        return prompt

    def wait_for_completion(self, prompt_id, timeout=300):
        start_time = time.time()
        while time.time() - start_time < timeout:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                return history[prompt_id]
            time.sleep(1)
        raise TimeoutError(f"Task {prompt_id} timed out")

# Test execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ComfyUI API Client")
    parser.add_argument("--server", default="127.0.0.1:8188", help="ComfyUI server address")
    parser.add_argument("--workflow", default="/root/projects/TMLSR/workflows/seedvr2_simple.json", help="Path to workflow JSON")
    parser.add_argument("--input", default="/root/projects/TMLSR/test_input.png", help="Path to input image")
    parser.add_argument("--output-prefix", default="api_test_output", help="Output filename prefix")
    parser.add_argument("--api-key", help="ComfyUI API Key (if required)")
    args = parser.parse_args()

    client = ComfyUIClient(server_address=args.server)
    
    if not client.check_health():
        print(f"Error: Could not connect to ComfyUI at {client.base_url}")
        print("Please ensure ComfyUI is running and accessible.")
        # We exit here because we cannot proceed without object_info
        exit(1)
    
    # Define paths
    if args.workflow:
        workflow_path = args.workflow
    else:
        # Default to the known workflow file
        workflow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "▶SeedVR2简单.json")
        if not os.path.exists(workflow_path):
            # Try without directory traversal if running from root
            workflow_path = "/root/projects/TMLSR/▶SeedVR2简单.json"
            if not os.path.exists(workflow_path):
                # Try relative path
                workflow_path = "▶SeedVR2简单.json"
                if not os.path.exists(workflow_path):
                    print(f"Error: Default workflow file not found at {workflow_path}")
                    print("Please specify a workflow file with --workflow")
                    exit(1)

    input_image_path = args.input # Need a test image
    
    # Create a dummy test image if not exists
    if not os.path.exists(input_image_path):
        import cv2
        import numpy as np
        img = np.zeros((512, 512, 3), dtype=np.uint8)
        cv2.putText(img, 'Test', (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 5, (255, 255, 255), 5)
        cv2.imwrite(input_image_path, img)
        
    print("Uploading image...")
    upload_res = client.upload_image(input_image_path, overwrite=True)
    uploaded_filename = upload_res['name']
    print(f"Uploaded: {uploaded_filename}")
    
    print("Loading workflow...")
    with open(workflow_path, 'r', encoding='utf-8') as f:
        ui_json = json.load(f)
        
    print("Converting workflow...")
    prompt = client.convert_ui_to_api(ui_json)
    
    # Modify Input Node (ID 12)
    # The LoadImage node in "SeedVR2简单.json" might have a different ID.
    # We need to find the LoadImage node dynamically if ID 12 is not it.
    
    load_image_node_id = None
    save_image_node_id = None
    
    for node_id, node_data in prompt.items():
        if node_data['class_type'] == 'LoadImage':
            load_image_node_id = node_id
        elif node_data['class_type'] == 'SaveImage':
            save_image_node_id = node_id
            
    if load_image_node_id:
        print(f"Found LoadImage node ID: {load_image_node_id}")
        prompt[load_image_node_id]["inputs"]["image"] = uploaded_filename
    else:
        print("Error: No LoadImage node found in workflow")
        # Fallback to ID 12 just in case
        if "12" in prompt:
             prompt["12"]["inputs"]["image"] = uploaded_filename

    # Modify Output Node - optional
    if save_image_node_id:
        print(f"Found SaveImage node ID: {save_image_node_id}")
        prompt[save_image_node_id]["inputs"]["filename_prefix"] = args.output_prefix
    else:
         if "22" in prompt:
            prompt["22"]["inputs"]["filename_prefix"] = args.output_prefix
        
    print("Queueing prompt...")
    try:
        res = client.queue_prompt(prompt, api_key=args.api_key)
        prompt_id = res['prompt_id']
        print(f"Prompt ID: {prompt_id}")
        
        print("Waiting for completion...")
        history = client.wait_for_completion(prompt_id)
        print("Task complete!")
        
        # Parse outputs
        outputs = history['outputs']
        for node_id, output_data in outputs.items():
            if 'images' in output_data:
                for img in output_data['images']:
                    fname = img['filename']
                    ftype = img['type']
                    print(f"Output Image: {fname} (Type: {ftype})")
                    
                    # Download image
                    try:
                        img_data = client.get_image(fname, img['subfolder'], ftype)
                        save_path = os.path.join(os.path.dirname(workflow_path), f"result_{fname}")
                        with open(save_path, "wb") as f:
                            f.write(img_data)
                        print(f"Saved result to: {save_path}")
                    except Exception as e:
                        print(f"Failed to download image: {e}")
                    
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.read().decode()}")
    except Exception as e:
        print(f"Error: {e}")
