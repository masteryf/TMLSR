import os
import cv2
import torch
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from basicsr.archs.rrdbnet_arch import RRDBNet
# Import from sibling package
try:
    from realesrgan import RealESRGANer
except ImportError:
    # Fallback or relative import
    try:
        from ..realesrgan import RealESRGANer
    except ImportError:
         raise ImportError("Could not import RealESRGANer. Make sure 'realesrgan' package is in python path.")

class ImageSRProcessor:
    def __init__(self, model_path=None, scale=4, gpu_id=0, tile=0, tile_pad=10, pre_pad=0, fp32=False):
        """
        Initialize the Super-Resolution Processor.
        
        Args:
            model_path (str): Path to the model weights. Defaults to 'weights/RealESRGAN_x4plus.pth' relative to this file's package.
            scale (int): Upsampling scale. Default 4.
            gpu_id (int): GPU ID to use. None for CPU.
            tile (int): Tile size for tiled processing. 0 for no tiling.
            tile_pad (int): Tile padding.
            pre_pad (int): Pre-padding.
            fp32 (bool): Use FP32 precision. False for FP16 (faster).
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() and (gpu_id is None or gpu_id >= 0) else 'cpu')
        self.scale = scale
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if model_path is None:
            # Default to weights directory in the package
            model_path = os.path.join(base_dir, 'weights', 'RealESRGAN_x4plus.pth')
        elif not os.path.exists(model_path):
            # Try looking in weights directory if provided path doesn't exist
            potential_path = os.path.join(base_dir, 'weights', model_path)
            if os.path.exists(potential_path):
                model_path = potential_path
            
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at: {model_path}")
            
        print(f"Loading model from {model_path} on {self.device}...")
        
        # Initialize model architecture
        # Auto-detect block number for anime 6B model
        num_block = 23
        if '6B' in os.path.basename(model_path):
            num_block = 6
            print("Detected 6B model, using num_block=6")
            
        self.model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=num_block, num_grow_ch=32, scale=scale)
        
        self.upsampler = RealESRGANer(
            scale=scale,
            model_path=model_path,
            model=self.model,
            tile=tile,
            tile_pad=tile_pad,
            pre_pad=pre_pad,
            half=not fp32,
            gpu_id=gpu_id
        )
        print("Model loaded successfully.")

    def cleanup(self):
        """Explicitly release model and CUDA memory."""
        if hasattr(self, 'upsampler'):
            del self.upsampler
        if hasattr(self, 'model'):
            del self.model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    def process_image(self, img_input, output_path=None, outscale=None, output_dims=None):
        """
        Process a single image.
        
        Args:
            img_input (str or np.ndarray): Input image path or numpy array (BGR).
            output_path (str): Output path to save the image. If None, returns the image array.
            outscale (float): The intermediate SR upsampling scale. If None, uses model's default scale.
            output_dims (tuple): (width, height) to resize to after SR. If None, no resize.
            
        Returns:
            np.ndarray: Enhanced image if output_path is None, else None.
        """
        if isinstance(img_input, str):
            img = cv2.imread(img_input, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError(f"Could not read image from {img_input}")
        else:
            img = img_input

        try:
            # Use provided outscale or default to self.scale
            target_scale = outscale if outscale is not None else self.scale
            
            # SR Process
            output, _ = self.upsampler.enhance(img, outscale=target_scale)
            
            # Post-SR Resize if output_dims is specified
            if output_dims is not None:
                # cv2.resize expects (width, height)
                output = cv2.resize(output, output_dims, interpolation=cv2.INTER_LANCZOS4)
            
            if output_path:
                cv2.imwrite(output_path, output)
                return None
            else:
                return output
        except RuntimeError as error:
            print(f"Error processing image: {error}")
            raise

    def process_batch(self, input_paths, output_paths, max_workers=4, outscale=None, output_dims_list=None, progress_callback=None):
        """
        Process a batch of images in parallel.
        
        Args:
            input_paths (list): List of input image paths.
            output_paths (list): List of output image paths.
            max_workers (int): Number of worker threads.
            outscale (float): Scale factor for SR.
            output_dims_list (list): List of (w, h) tuples corresponding to each input. If None, no resize.
            progress_callback (callable): Function called with (completed_count, total_count).
        """
        if len(input_paths) != len(output_paths):
            raise ValueError("Input and output lists must have same length")
        
        if output_dims_list and len(output_dims_list) != len(input_paths):
            raise ValueError("Output dims list must match input length")

        tasks = []
        for i in range(len(input_paths)):
            dims = output_dims_list[i] if output_dims_list else None
            tasks.append((input_paths[i], output_paths[i], dims))
        
        total_tasks = len(tasks)
        print(f"Processing {total_tasks} images with {max_workers} workers...")
        
        completed_count = 0
        if progress_callback:
            progress_callback(0, total_tasks)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.process_image, inp, out, outscale, dims) 
                for inp, out, dims in tasks
            ]
            
            for i, future in enumerate(futures):
                try:
                    future.result()
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, total_tasks)
                except Exception as e:
                    print(f"Failed to process {input_paths[i]}: {e}")
        
        print("Batch processing complete.")
