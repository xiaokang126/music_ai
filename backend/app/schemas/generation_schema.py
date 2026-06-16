from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class GenerationSessionCreate(BaseModel):
    project_id: str


class GenerationTaskItem(BaseModel):
    id: str
    segment_idx: int
    ace_task_id: str = ""
    prompt: str
    status: str
    audio_path: str = ""
    audio_url: str = ""
    error_msg: str = ""
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerationSessionResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    status: str
    total_tasks: int
    completed_tasks: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    tasks: List[GenerationTaskItem] = []

    class Config:
        from_attributes = True


class GenerationTaskUpdate(BaseModel):
    status: Optional[str] = None
    audio_path: Optional[str] = None
    audio_url: Optional[str] = None
    error_msg: Optional[str] = None
