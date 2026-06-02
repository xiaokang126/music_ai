from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..middleware.auth import get_current_user
from ..services.resonance_service import find_resonance_works

router = APIRouter(prefix="/api/resonance", tags=["resonance"])


@router.get("/match")
def match_resonance(mood: str = "", db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not mood:
        # Get user's latest mood from their works
        from ..models.music_work import MusicWork
        from sqlalchemy import desc
        last_work = db.query(MusicWork).filter(
            MusicWork.user_id == user.id
        ).order_by(desc(MusicWork.created_at)).first()
        mood = last_work.mood_tag if last_work else "melancholic"

    works = find_resonance_works(db, mood, user.id)
    return {"works": works, "base_mood": mood}
