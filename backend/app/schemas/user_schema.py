from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=500000)


class UserResponse(BaseModel):
    id: str
    username: str
    avatar_url: Optional[str] = ""
    avatar: Optional[str] = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    token: str
    user: UserResponse
