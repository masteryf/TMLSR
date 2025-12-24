# TMLSR (Video/Image Super-Resolution Service)

TMLSR is a high-performance, production-ready service for video and image super-resolution using Real-ESRGAN. It provides a robust API for submitting tasks, tracking progress, and managing results, along with a built-in monitoring dashboard.

## Features

- **High-Quality Super-Resolution**: Uses Real-ESRGAN for state-of-the-art restoration.
- **Video & Image Support**: Handles both video (.mp4) and image (.png, .jpg) inputs.
- **Customizable Output**: Supports defining output magnification and dimensions.
- **Production Ready**:
  - **Task Queue**: Manages concurrent tasks with a configurable worker pool.
  - **Reliability**: Automatic retries for failed tasks and error isolation.
  - **OSS Integration**: Seamlessly uploads/downloads files from Aliyun OSS.
  - **Monitoring Dashboard**: Real-time visualization of server status and task progress.

## Directory Structure

```
TMLSR/
├── config.yaml          # Configuration file (OSS, Server settings)
├── requirements.txt     # Python dependencies
├── start_server.py      # Server entry point
├── server/              # Server source code
│   ├── main.py          # FastAPI app & routes
│   ├── task_manager.py  # Task management logic
│   ├── models.py        # Pydantic data models
│   └── static/          # Dashboard frontend assets
├── utils/               # Core processing utilities
│   ├── image_sr.py      # Image super-resolution processor
│   ├── video_sr.py      # Video super-resolution processor
│   └── oss_handler.py   # Aliyun OSS handler
└── weights/             # Model weights
```

## Installation

1.  **Prerequisites**:
    *   Python 3.8+
    *   CUDA-capable GPU (recommended)
    *   FFmpeg (installed and added to system PATH)

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: For `basicsr`, you might need to follow their specific installation guide if you encounter issues.*

3.  **Configuration**:
    Edit `config.yaml` to set your OSS credentials and server preferences:
    ```yaml
    oss:
      endpoint: "oss-cn-hongkong.aliyuncs.com"
      accessKey: "your_access_key"
      accessSecret: "your_access_secret"
      bucketName: "your_bucket_name"

    server:
      max_workers: 2      # Number of concurrent SR tasks
      max_retries: 3      # Max retries for failed tasks
      retry_delay: 5      # Seconds to wait before retry
    ```

## Usage

### Starting the Server

```bash
python start_server.py
```
The server will start at `http://0.0.0.0:8000`.

### Monitoring Dashboard

Visit `http://localhost:8000/dashboard` to view the server status, active tasks, and system metrics.

### API Usage

See [API Documentation](API.md) for detailed endpoint descriptions.

## License

MIT
