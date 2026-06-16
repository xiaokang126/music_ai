import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.dialects.sqlite import CHAR
from sqlalchemy.sql import func
from ..database import Base


class MusicTimeline(Base):
    __tablename__ = "music_timelines"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        CHAR(36),
        ForeignKey("video_projects.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    style = Column(String(100), default="")
    bpm = Column(String(20), default="")
    key = Column(String(10), default="")
    duration = Column(Float, default=0.0)
    global_caption = Column(Text, default="")
    timeline_json = Column(Text, default="[]")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
