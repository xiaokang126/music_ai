import uuid
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.sqlite import CHAR
from sqlalchemy.sql import func
from ..database import Base


class UserSFX(Base):
    """User-uploaded sound effect files."""
    __tablename__ = "user_sfxs"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    sfx_type = Column(String(30), default="custom")  # whoosh/hit/impact/riser/custom
    filename = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False)
    duration = Column(String(20), default="0")
    created_at = Column(DateTime, server_default=func.now())


class UserInspiration(Base):
    """User-submitted inspiration/mood-board items."""
    __tablename__ = "user_inspirations"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    theme = Column(String(50), default="")        # 主题：校园/爱情/旅行/...
    emotion = Column(String(30), default="warm")   # calm/warm/happy/...
    reference_url = Column(String(512), default="") # 参考链接(视频/音乐URL)
    tags = Column(Text, default="[]")               # JSON array of tags
    likes_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
