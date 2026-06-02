from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from ..database import Base


class EmotionDiary(Base):
    __tablename__ = "emotion_diaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mood_tag = Column(String(50), nullable=False)
    mood_score = Column(Float, nullable=False)
    note = Column(String(500), default="")
    work_id = Column(Integer, ForeignKey("music_works.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
