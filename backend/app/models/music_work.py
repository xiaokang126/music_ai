from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from ..database import Base


class MusicWork(Base):
    __tablename__ = "music_works"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    mood_tag = Column(String(50), default="")
    params_json = Column(Text, nullable=False)
    reply_to_work_id = Column(Integer, ForeignKey("music_works.id"), nullable=True, index=True)
    is_public = Column(Boolean, default=True)
    likes_count = Column(Integer, default=0)
    description = Column(String(500), default="")
    created_at = Column(DateTime, server_default=func.now())
