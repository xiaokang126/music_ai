from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CommunityPostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    project_id: Optional[str] = None
    description: str = Field(default="")
    story_tags: List[str] = Field(default_factory=list)
    content: str = Field(default="")
    media_url: str = Field(default="")
    is_anonymous: bool = Field(default=False)


class CommunityPostResponse(BaseModel):
    id: str
    user_id: str
    project_id: Optional[str] = None
    title: str
    content: str
    description: str = ""
    story_tags: str = "[]"
    likes_count: int = 0
    comments_count: int = 0
    collects_count: int = 0
    is_liked: bool = False
    is_anonymous: bool = False
    can_delete: bool = False
    created_at: Optional[datetime] = None
    username: Optional[str] = None

    class Config:
        from_attributes = True


class CommunityPostListResponse(BaseModel):
    posts: List[CommunityPostResponse]
    total: int
    page: int
    page_size: int


class CommentCreate(BaseModel):
    post_id: str
    content: str = Field(..., min_length=1, max_length=500)


class CommentResponse(BaseModel):
    id: str
    post_id: str
    user_id: str
    content: str
    created_at: datetime
    username: Optional[str] = None

    class Config:
        from_attributes = True


class LikeCreate(BaseModel):
    post_id: str


class CommunityRuleCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)


class CommunityRuleUser(BaseModel):
    user_id: str
    username: str
    created_at: Optional[datetime] = None


class CommunitySettingsResponse(BaseModel):
    hidden_authors: List[CommunityRuleUser] = Field(default_factory=list)
    blocked_viewers: List[CommunityRuleUser] = Field(default_factory=list)
