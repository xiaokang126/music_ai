from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GiftResponse(BaseModel):
    id: int
    name: str
    icon: str
    type: str

    class Config:
        from_attributes = True


class WorkGiftResponse(BaseModel):
    id: int
    work_id: int
    sender_id: int
    gift_id: int
    sender_name: Optional[str] = None
    gift_name: Optional[str] = None
    gift_icon: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GiftSendRequest(BaseModel):
    gift_id: int


class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: int
    work_id: int
    user_id: int
    content: str
    username: Optional[str] = None
    avatar: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
