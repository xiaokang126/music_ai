from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ExportTaskCreate(BaseModel):
    project_id: str
    format: str = Field(default="mp4")


class ExportTaskResponse(BaseModel):
    id: str
    project_id: str
    format: str
    file_path: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
