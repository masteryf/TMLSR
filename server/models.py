from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, HttpUrl, Field

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class TaskType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"

class TaskCreateRequest(BaseModel):
    url: str = Field(..., description="HTTP URL or file path")
    type: TaskType = TaskType.VIDEO
    outscale: Optional[float] = Field(None, description="Intermediate SR upsampling scale. e.g. 4")
    output_magnification: Optional[float] = Field(None, description="Final output scale relative to original. e.g. 1.5")
    
    # Optional parameters for compatibility or advanced tuning
    vcodec: Optional[str] = "libx264"
    acodec: Optional[str] = "aac"
    audio: bool = True
    gpu_id: int = 0
    model: Optional[str] = Field("RealESRGAN_x4plus.pth", description="Model filename in weights directory")
    
    # Deprecated but kept for compatibility (ignored in logic if not needed, or mapped if possible)
    target: Optional[str] = None 

class TaskStage(BaseModel):
    name: str
    status: str
    duration: float = 0.0

class TaskOutput(BaseModel):
    url: Optional[str] = None
    size_mb: Optional[float] = None

class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: str
    updated_at: str
    params: Dict[str, Any]
    stages: List[TaskStage] = []
    output: Optional[TaskOutput] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
