from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DiaryCreate(BaseModel):
    mood_tag: str
    mood_score: float
    note: str = ""
    work_id: Optional[int] = None


class DiaryResponse(BaseModel):
    id: int
    user_id: int
    mood_tag: str
    mood_score: float
    note: str
    work_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChartDataPoint(BaseModel):
    date: str
    score: float
    mood_tag: str


class DiaryChartResponse(BaseModel):
    points: List[ChartDataPoint]
