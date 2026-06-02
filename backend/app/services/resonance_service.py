from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.music_work import MusicWork
from ..models.user import User


def find_resonance_works(db: Session, mood_tag: str, exclude_user_id: int, limit: int = 10):
    works = db.query(MusicWork).filter(
        MusicWork.is_public == True,
        MusicWork.user_id != exclude_user_id
    ).order_by(func.random()).limit(limit * 3).all()

    scored = []
    for w in works:
        score = _calc_similarity(mood_tag, w.mood_tag)
        if score > 0.3:
            scored.append((w, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    scored = scored[:limit]

    result = []
    for w, score in scored:
        user = db.query(User).filter(User.id == w.user_id).first()
        result.append({
            "id": w.id, "user_id": w.user_id, "title": w.title,
            "mood_tag": w.mood_tag, "params_json": w.params_json,
            "reply_to_work_id": w.reply_to_work_id, "is_public": w.is_public,
            "likes_count": w.likes_count, "description": w.description,
            "created_at": w.created_at,
            "username": user.username if user else "",
            "avatar": user.avatar if user else "",
            "match_score": round(score * 100),
        })
    return result


def _calc_similarity(mood1: str, mood2: str) -> float:
    if mood1 == mood2:
        return 1.0
    neighbors = {
        "melancholic": {"sad": 0.9, "nostalgic": 0.8, "lonely": 0.8, "bittersweet": 0.7, "calm": 0.4},
        "sad": {"melancholic": 0.9, "lonely": 0.85, "bittersweet": 0.7, "nostalgic": 0.6},
        "hopeful": {"healing": 0.9, "warm": 0.8, "calm": 0.5},
        "calm": {"peaceful": 0.9, "healing": 0.7, "warm": 0.5},
        "nostalgic": {"melancholic": 0.8, "bittersweet": 0.7, "warm": 0.5},
        "healing": {"hopeful": 0.9, "warm": 0.8, "calm": 0.7},
        "lonely": {"sad": 0.85, "melancholic": 0.8},
        "bittersweet": {"melancholic": 0.7, "sad": 0.7, "nostalgic": 0.7},
        "warm": {"hopeful": 0.8, "healing": 0.8, "calm": 0.5},
        "peaceful": {"calm": 0.9, "healing": 0.6},
    }
    if mood1 in neighbors and mood2 in neighbors[mood1]:
        return neighbors[mood1][mood2]
    if mood2 in neighbors and mood1 in neighbors[mood2]:
        return neighbors[mood2][mood1]
    return 0.1
