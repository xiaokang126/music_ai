import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.sqlite import CHAR
from sqlalchemy.sql import func
from ..database import Base


class ExportTask(Base):
    __tablename__ = "export_tasks"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(CHAR(36), ForeignKey("video_projects.id"), nullable=False, index=True)
    format = Column(String(10), nullable=False)  # mp4/wav/flac/mp3/json
    file_path = Column(String(512), default="")
    file_url = Column(String(512), default="")
    status = Column(String(20), nullable=False, default="processing")  # processing/completed/failed
    error_msg = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
