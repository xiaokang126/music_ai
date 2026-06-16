import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.sqlite import CHAR
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    avatar_url = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
