from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models.emotion_diary import EmotionDiary


def create_diary_entry(db: Session, user_id: int, mood_tag: str, mood_score: float,
                       note: str = "", work_id: int = None):
    entry = EmotionDiary(
        user_id=user_id, mood_tag=mood_tag, mood_score=mood_score,
        note=note, work_id=work_id
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_user_diary(db: Session, user_id: int, page: int = 1, page_size: int = 30):
    query = db.query(EmotionDiary).filter(EmotionDiary.user_id == user_id).order_by(desc(EmotionDiary.created_at))
    total = query.count()
    entries = query.offset((page - 1) * page_size).limit(page_size).all()
    return entries, total


def get_mood_chart_data(db: Session, user_id: int, days: int = 30):
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)
    entries = db.query(EmotionDiary).filter(
        EmotionDiary.user_id == user_id,
        EmotionDiary.created_at >= since
    ).order_by(EmotionDiary.created_at).all()

    points = []
    for e in entries:
        points.append({
            "date": e.created_at.strftime("%m-%d"),
            "score": e.mood_score,
            "mood_tag": e.mood_tag
        })
    return points
