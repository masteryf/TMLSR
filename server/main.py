from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from .models import (
    TaskCreateRequest, 
    TaskResponse, 
    HealthResponse, 
    TaskStatus
)
from .task_manager import task_manager

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

app = FastAPI(
    title="Video Super Resolution Service",
    version="1.0.0",
    description="Service for Video and Image Super-Resolution using Real-ESRGAN"
)

# Ensure static directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

app.mount("/dashboard", StaticFiles(directory=static_dir, html=True), name="dashboard")

@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")

@app.get("/monitor/stats")
async def get_monitor_stats():
    return task_manager.get_monitor_stats()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {"status": "ok"}

@app.post("/tasks", response_model=dict, status_code=status.HTTP_200_OK)
async def create_task(request: TaskCreateRequest):
    """
    Submit a super-resolution task.
    """
    task_id = task_manager.create_task(request)
    return {"status": "ok", "task_id": task_id}

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """
    Get task status and details.
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a running or pending task.
    """
    success = task_manager.cancel_task(task_id)
    if success:
        return {"status": "canceled"}
    else:
        # Task might be completed or doesn't exist
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        raise HTTPException(status_code=400, detail="Unable to cancel task (already completed or failed)")
