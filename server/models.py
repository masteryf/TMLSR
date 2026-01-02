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
    model: Optional[str] = Field(None, description="Workflow name (e.g. SeedVR2Defeat) or legacy model name")
    workflow: Optional[str] = Field(None, description="Workflow name to use. Overrides model.")
    
    # Deprecated fields
    outscale: Optional[float] = Field(None, description="Deprecated. Use workflow settings.")
    output_magnification: Optional[float] = Field(None, description="Deprecated. Use workflow settings.")
    resolution: Optional[int] = Field(None, description="Deprecated. Use workflow settings.")
    
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
