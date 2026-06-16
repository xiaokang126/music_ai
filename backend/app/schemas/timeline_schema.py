from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TimelineGenerateRequest(BaseModel):
    project_id: str
    style: str = "campus_memory"


class TimelineRestyleRequest(BaseModel):
    new_style: str


class TimelineUpdateRequest(BaseModel):
    style: Optional[str] = None
    bpm: Optional[int] = None
    key: Optional[str] = None
    timeline_json: Optional[str] = None
    global_caption: Optional[str] = None


class TimelineResponse(BaseModel):
    id: str
    project_id: str
    style: str
    bpm: str
    key: str
    duration: float
    global_caption: str
    timeline_json: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
