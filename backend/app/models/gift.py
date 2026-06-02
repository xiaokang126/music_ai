from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from ..database import Base


class Gift(Base):
    __tablename__ = "gifts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    icon = Column(String(50), nullable=False)
    type = Column(String(20), default="free")
    created_at = Column(DateTime, server_default=func.now())


class WorkGift(Base):
    __tablename__ = "work_gifts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_id = Column(Integer, ForeignKey("music_works.id"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    gift_id = Column(Integer, ForeignKey("gifts.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
