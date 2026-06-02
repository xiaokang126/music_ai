from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from ..database import Base


class HealingPlan(Base):
    __tablename__ = "healing_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), default="")
    duration_days = Column(Integer, nullable=False)
    cover_icon = Column(String(50), default="heart")
    tasks_json = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class UserHealingPlan(Base):
    __tablename__ = "user_healing_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("healing_plans.id"), nullable=False)
    current_day = Column(Integer, default=1)
    start_date = Column(DateTime, server_default=func.now())
    completed_tasks_json = Column(Text, default="[]")
    is_completed = Column(Integer, default=0)
