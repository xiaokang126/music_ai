import uuid
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.sqlite import CHAR
from sqlalchemy.sql import func
from ..database import Base


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(CHAR(36), ForeignKey("video_projects.id"), nullable=True)
    title = Column(String(200), nullable=False)
    story_tags = Column(Text, default="[]")  # JSON array
    description = Column(Text, default="")
    cover_url = Column(String(512), default="")
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    collects_count = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    is_anonymous = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class Comment(Base):
    __tablename__ = "comments"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(CHAR(36), ForeignKey("community_posts.id"), nullable=False, index=True)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Like(Base):
    __tablename__ = "likes"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(CHAR(36), ForeignKey("community_posts.id"), nullable=False)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Collect(Base):
    __tablename__ = "collects"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(CHAR(36), ForeignKey("community_posts.id"), nullable=False)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class CommunityVisibilityRule(Base):
    """Per-user community privacy/feed preference.

    mode=hide_author: owner does not want to see target author's posts.
    mode=block_viewer: owner does not want target viewer to see owner's posts.
    """
    __tablename__ = "community_visibility_rules"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    target_user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    mode = Column(String(30), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
