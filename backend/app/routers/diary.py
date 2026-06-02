from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.diary import DiaryCreate
from ..middleware.auth import get_current_user
from ..services.diary_service import create_diary_entry, get_user_diary, get_mood_chart_data

router = APIRouter(prefix="/api/diary", tags=["diary"])


@router.post("")
def add_diary(data: DiaryCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    entry = create_diary_entry(db, user.id, data.mood_tag, data.mood_score, data.note, data.work_id)
    return {
        "id": entry.id, "user_id": entry.user_id, "mood_tag": entry.mood_tag,
        "mood_score": entry.mood_score, "note": entry.note,
        "work_id": entry.work_id, "created_at": entry.created_at
    }


@router.get("")
def list_diary(page: int = Query(1, ge=1), db: Session = Depends(get_db), user=Depends(get_current_user)):
    entries, total = get_user_diary(db, user.id, page)
    result = []
    for e in entries:
        result.append({
            "id": e.id, "user_id": e.user_id, "mood_tag": e.mood_tag,
            "mood_score": e.mood_score, "note": e.note,
            "work_id": e.work_id, "created_at": e.created_at
        })
    return {"entries": result, "total": total}


@router.get("/chart")
def mood_chart(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db), user=Depends(get_current_user)):
    points = get_mood_chart_data(db, user.id, days)
    return {"points": points}
