from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class HealingPlanResponse(BaseModel):
    id: int
    name: str
    description: str
    duration_days: int
    cover_icon: str
    tasks_json: str

    class Config:
        from_attributes = True


class UserHealingPlanResponse(BaseModel):
    id: int
    user_id: int
    plan_id: int
    current_day: int
    start_date: datetime
    completed_tasks_json: str
    is_completed: int
    plan_name: Optional[str] = None

    class Config:
        from_attributes = True
