from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class WorkCreate(BaseModel):
    title: str
    mood_tag: str = ""
    params_json: str
    reply_to_work_id: Optional[int] = None
    description: str = ""


class WorkResponse(BaseModel):
    id: int
    user_id: int
    title: str
    mood_tag: str
    params_json: str
    reply_to_work_id: Optional[int] = None
    is_public: bool
    likes_count: int
    description: str
    created_at: datetime
    username: Optional[str] = None
    avatar: Optional[str] = None
    reply_count: Optional[int] = 0
    gift_count: Optional[int] = 0
    comment_count: Optional[int] = 0

    class Config:
        from_attributes = True


class WorkListResponse(BaseModel):
    works: List[WorkResponse]
    total: int
    page: int
    page_size: int
