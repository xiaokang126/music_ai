import uuid
import enum
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.sqlite import CHAR
from sqlalchemy.sql import func
from ..database import Base


class VideoTypeEnum(str, enum.Enum):
    healing_vlog = "healing_vlog"
    product_promo = "product_promo"
    hype_edit = "hype_edit"
    campus_memory = "campus_memory"
    emotional_story = "emotional_story"
    knowledge_edu = "knowledge_edu"


class VideoProject(Base):
    __tablename__ = "video_projects"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), default="Untitled")
    video_filename = Column(String(256), nullable=False)
    video_path = Column(String(512), nullable=False)
    video_type = Column(String(30), nullable=False, default="campus_memory")
    user_description = Column(Text, default="")
    status = Column(String(20), nullable=False, default="uploaded")
    metadata_json = Column(Text, default="{}")
    video_profile = Column(Text, default="")
    key_points_json = Column(Text, default="[]")
    voice_regions_json = Column(Text, default="[]")
    caption_events_json = Column(Text, default="[]")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
