# TMLSR API Documentation

Base URL: `http://localhost:6008`

## Endpoints

### 1. Health Check
Check if the server is running.

- **URL**: `/health`
- **Method**: `GET`
- **Response**:
    ```json
    {
        "status": "ok"
    }
    ```

### 2. Create Task
Submit a new super-resolution task for video or image.

- **URL**: `/tasks`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Body Parameters**:

| Field | Type | Required | Description |
|---|---|---|---|
| `url` | string | Yes | The URL of the input file (OSS URL or accessible HTTP URL). |
| `type` | string | No | `video` or `image`. Defaults to `video`. |
| `model` | string | No | Model filename in `weights/` directory (e.g. `realesr-animevideov3.pth`). Defaults to `realesr-animevideov3.pth`. |
| `outscale` | float | No | The super-resolution scale factor (e.g., 2, 4). Defaults to model scale (usually 4). |
| `output_magnification` | float | No | The final output magnification relative to the original size. If provided, the result will be resized to this magnification after SR. |
| `output_dims` | [int, int] | No | Specific output dimensions `[width, height]`. Overrides `output_magnification` if provided. |
| `resolution` | int | No | Target output height (e.g. 1080). **Only used when model contains "seedvr2".** If provided, it overrides `outscale` and `output_magnification`. |

- **Example Request (Standard)**:
    ```json
    {
        "url": "https://oss-bucket.aliyuncs.com/input/video.mp4",
        "type": "video",
        "outscale": 4,
        "output_magnification": 1.5
    }
    ```
    *Explanation: The video will be upscaled 4x by the model, and then resized to 1.5x of the original resolution.*

- **Example Request (SeedVR2)**:
    ```json
    {
        "url": "http://example.com/image.png",
        "type": "image",
        "model": "seedvr2_ema_3b-Q4_K_M.gguf",
        "resolution": 1080
    }
    ```
    *Explanation: Use SeedVR2 model to upscale image to 1080p height. `outscale` and `output_magnification` are ignored.*

- **Response**:
    ```json
    {
        "status": "ok",
        "task_id": "32c9e3a093344687b8918231234abcd"
    }
    ```

### 3. Get Task Status
Retrieve the status and details of a specific task.

- **URL**: `/tasks/{task_id}`
- **Method**: `GET`
- **Response**:
    ```json
    {
        "task_id": "32c9e3a093344687b8918231234abcd",
        "status": "completed",
        "created_at": "2023-10-27T10:00:00Z",
        "updated_at": "2023-10-27T10:05:00Z",
        "params": { ... },
        "stages": [
            { "name": "download", "status": "success", "duration": 2.5 },
            { "name": "process", "status": "success", "duration": 120.0 },
            { "name": "upload", "status": "success", "duration": 3.0 }
        ],
        "output": {
            "url": "https://oss-bucket.aliyuncs.com/output/output_video.mp4",
            "metadata": { ... }
        },
        "error": null
    }
    ```

### 4. Cancel Task
Cancel a pending or running task.

- **URL**: `/tasks/{task_id}`
- **Method**: `DELETE`
- **Response**:
    ```json
    {
        "status": "canceled"
    }
    ```

### 5. Monitor Stats
Get server system statistics and recent tasks (used by Dashboard).

- **URL**: `/monitor/stats`
- **Method**: `GET`
- **Response**:
    ```json
    {
        "system": {
            "max_workers": 2,
            "active_workers": 1,
            "queue_size": 0
        },
        "stats": {
            "pending": 0,
            "processing": 1,
            "completed": 10,
            "failed": 0,
            "canceled": 0
        },
        "tasks": [ ... ]
    }
    ```
