from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class KeyPointItem(BaseModel):
    time: float = 0
    type: str = "custom"
    label: str = ""
    importance: str = "normal"
    description: str = ""


class VoiceRegionItem(BaseModel):
    start: float = 0
    end: float = 0
    type: str = "dialogue"
    content: str = ""


class CaptionEventItem(BaseModel):
    time: float = 0
    text: str = ""
    style: str = "subtitle"


class KeyPointsRequest(BaseModel):
    keypoints: List[KeyPointItem] = []
    voice_regions: List[VoiceRegionItem] = []
    caption_events: List[CaptionEventItem] = []


class VideoProjectResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    title: str
    video_filename: str
    video_type: str
    user_description: str
    status: str
    metadata_json: Optional[str] = None
    video_profile: Optional[str] = None
    duration: float = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VideoProjectListResponse(BaseModel):
    projects: List[VideoProjectResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
