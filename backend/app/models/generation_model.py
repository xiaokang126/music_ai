import uuid
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ForeignKey
from sqlalchemy.dialects.sqlite import CHAR
from sqlalchemy.sql import func
from ..database import Base


class GenerationSession(Base):
    __tablename__ = "generation_sessions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(CHAR(36), ForeignKey("video_projects.id"), nullable=False, index=True)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    full_audio_path = Column(String(512), default="")
    full_audio_url = Column(String(512), default="")
    status = Column(String(20), nullable=False, default="pending")  # pending/segmenting/completed/failed
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)


class GenerationTask(Base):
    __tablename__ = "generation_tasks"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(CHAR(36), ForeignKey("generation_sessions.id"), nullable=False, index=True)
    project_id = Column(CHAR(36), ForeignKey("video_projects.id"), nullable=False)
    segment_idx = Column(Integer, nullable=False)
    ace_task_id = Column(String(128), default="")
    prompt = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending/submitted/processing/completed/failed
    audio_path = Column(String(512), default="")
    audio_url = Column(String(512), default="")
    error_msg = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
