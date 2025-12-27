import os
import shutil
import subprocess
import glob
import time
import cv2
from utils.image_sr import ImageSRProcessor

class VideoSRProcessor:
    def __init__(self, sr_processor: ImageSRProcessor = None, **kwargs):
        """
        Initialize VideoSRProcessor.
        
        Args:
            sr_processor (ImageSRProcessor): Existing ImageSRProcessor instance.
            **kwargs: Arguments to initialize a new ImageSRProcessor if one isn't provided (scale, gpu_id, etc).
        """
        if sr_processor:
            self.sr = sr_processor
        else:
            # Set default tile size if not provided to prevent OOM on large frames
            if 'tile' not in kwargs:
                kwargs['tile'] = 256 # Safe default for T4/1080p
            self.sr = ImageSRProcessor(**kwargs)

    def cleanup(self):
        """Release resources."""
        if self.sr:
            self.sr.cleanup()

    def _run_ffmpeg(self, cmd):
        """Helper to run ffmpeg commands."""
        # print(f"Executing: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg command failed: {' '.join(cmd)}")
            print(f"Error output: {e.stderr.decode()}")
            raise

    def process_video(self, input_path, output_path, temp_dir=None, max_workers=4, keep_audio=True, outscale=None, output_magnification=None, progress_callback=None):
        """
        Process a video file: split -> upsample -> merge.
        
        Args:
            input_path (str): Path to input video.
            output_path (str): Path to output video.
            temp_dir (str): Directory for temporary frames. Defaults to auto-generated.
            max_workers (int): Number of threads for frame processing IO.
            keep_audio (bool): Whether to copy audio from source.
            outscale (float): Intermediate SR scale (magnification).
            output_magnification (float): Final scale relative to original.
            progress_callback (callable): Optional callback for progress reporting.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")
            
        video_name = os.path.splitext(os.path.basename(input_path))[0]
        if temp_dir is None:
            # Create a unique temp dir based on timestamp
            temp_dir = f"temp_{video_name}_{int(time.time())}"
            
        # Define internal paths
        frames_in = os.path.join(temp_dir, "frames_in")
        frames_out = os.path.join(temp_dir, "frames_out")
        audio_path = os.path.join(temp_dir, "audio.aac")
        
        # Clean start
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(frames_in)
        os.makedirs(frames_out)
        
        try:
            print(f"--- Starting Video Super-Resolution for {input_path} ---")
            
            # 1. Get Metadata (FPS & Dims)
            cap = cv2.VideoCapture(input_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            if not fps or fps != fps: # Handle NaN
                print("Warning: Could not detect FPS, defaulting to 24.")
                fps = 24
            
            print(f"Video Info: {width}x{height}, FPS={fps}, Total Frames={frame_count}")
            
            # Determine Output Dims
            output_dims = None
            if output_magnification is not None:
                new_w = int(width * output_magnification)
                new_h = int(height * output_magnification)
                output_dims = (new_w, new_h)
                print(f"Target Resolution: {new_w}x{new_h}")

            # 2. Extract Frames
            print("Step 1/4: Extracting frames using FFmpeg...")
            # %08d.png ensures correct ordering for up to 100 million frames
            cmd_extract = [
                "ffmpeg", "-i", input_path, 
                "-q:v", "1", 
                os.path.join(frames_in, "%08d.png")
            ]
            self._run_ffmpeg(cmd_extract)
            
            # 3. Extract Audio
            has_audio = False
            if keep_audio:
                print("Step 2/4: Extracting audio...")
                try:
                    cmd_audio = [
                        "ffmpeg", "-i", input_path,
                        "-vn", "-acodec", "copy",
                        audio_path
                    ]
                    self._run_ffmpeg(cmd_audio)
                    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                        has_audio = True
                    else:
                        print("Audio file is empty or missing, proceeding without audio.")
                except Exception as e:
                    print(f"Audio extraction warning: {e}")

            # 4. Super-Resolution
            print("Step 3/4: Processing frames (Upsampling)...")
            frame_files = sorted(glob.glob(os.path.join(frames_in, "*.png")))
            if not frame_files:
                raise RuntimeError("No frames were extracted.")
            
            # Construct input/output pairs
            io_pairs = []
            for f in frame_files:
                basename = os.path.basename(f)
                out_f = os.path.join(frames_out, basename)
                io_pairs.append((f, out_f))
                
            inputs = [p[0] for p in io_pairs]
            outputs = [p[1] for p in io_pairs]
            
            # Prepare dims list
            output_dims_list = [output_dims] * len(inputs) if output_dims else None
            
            # Run batch processing
            
            def batch_progress(done, total):
                if progress_callback:
                    # SR is roughly 90% of work. We can map 0-100% of SR to maybe 10-95% of total task?
                    # But for simplicity, let's just report "Processing frames: X%"
                    pct = (done / total) * 100
                    progress_callback(pct, f"Processing frames {done}/{total}")

            self.sr.process_batch(
                inputs, 
                outputs, 
                max_workers=max_workers, 
                outscale=outscale, 
                output_dims_list=output_dims_list,
                progress_callback=batch_progress
            )

            # Check and repair missing frames to ensure FFmpeg sequence continuity
            out_files = sorted(glob.glob(os.path.join(frames_out, "*.png")))
            if not out_files:
                raise RuntimeError("No output frames were generated! Super-resolution process failed.")
            
            # Identify valid sample frame for fallback
            sample_frame_path = out_files[0]
            
            missing_count = 0
            for i, out_f in enumerate(outputs):
                if not os.path.exists(out_f):
                    missing_count += 1
                    # print(f"Warning: Frame {os.path.basename(out_f)} missing. Repairing...")
                    
                    # Strategy: Copy previous > Next > Sample
                    if i > 0 and os.path.exists(outputs[i-1]):
                         shutil.copy2(outputs[i-1], out_f)
                    elif i < len(outputs) - 1 and os.path.exists(outputs[i+1]):
                         shutil.copy2(outputs[i+1], out_f)
                    else:
                         shutil.copy2(sample_frame_path, out_f)
            
            if missing_count > 0:
                print(f"Repaired {missing_count} missing frames to ensure video continuity.")
            
            # 5. Merge
            print("Step 4/4: Merging frames into video...")
            # Note: glob pattern for ffmpeg sequence
            frame_pattern = os.path.join(frames_out, "%08d.png")
            
            cmd_merge = [
                "ffmpeg", "-r", str(fps),
                "-i", frame_pattern
            ]
            
            if has_audio:
                cmd_merge.extend(["-i", audio_path])
                
            cmd_merge.extend([
                "-c:v", "libx264", 
                "-pix_fmt", "yuv420p",
                "-crf", "18", # High quality
                "-y", output_path
            ])
            
            if has_audio:
                # Map video from input 0, audio from input 1
                cmd_merge.extend(["-map", "0:v:0", "-map", "1:a:0"])
            
            self._run_ffmpeg(cmd_merge)
            print(f"Success! Output saved to: {output_path}")
            
        except Exception as e:
            print(f"Error during video processing: {e}")
            raise
        finally:
            # 6. Cleanup
            print(f"Cleaning up cache: {temp_dir}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

if __name__ == '__main__':
    # Simple CLI test
    import sys
    if len(sys.argv) < 3:
        print("Usage: python video_sr.py <input_video> <output_video> [gpu_id]")
    else:
        inp = sys.argv[1]
        out = sys.argv[2]
        gpu = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        
        processor = VideoSRProcessor(gpu_id=gpu, scale=4)
        processor.process_video(inp, out)
