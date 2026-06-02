from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.gift import CommentCreate, CommentResponse
from ..middleware.auth import get_current_user
from ..models.comment import Comment
from ..models.user import User
from ..models.music_work import MusicWork

router = APIRouter(prefix="/api/works", tags=["comments"])


@router.get("/{work_id}/comments")
def list_comments(work_id: int, db: Session = Depends(get_db)):
    work = db.query(MusicWork).filter(MusicWork.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    comments = db.query(Comment, User).join(User, Comment.user_id == User.id).filter(
        Comment.work_id == work_id
    ).order_by(Comment.created_at.desc()).limit(50).all()

    result = []
    for c, u in comments:
        result.append({
            "id": c.id, "work_id": c.work_id, "user_id": c.user_id,
            "content": c.content, "username": u.username, "avatar": u.avatar,
            "created_at": c.created_at
        })
    return result


@router.post("/{work_id}/comments")
def create_comment(work_id: int, data: CommentCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    work = db.query(MusicWork).filter(MusicWork.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    comment = Comment(work_id=work_id, user_id=user.id, content=data.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {
        "id": comment.id, "work_id": comment.work_id, "user_id": comment.user_id,
        "content": comment.content, "username": user.username, "avatar": user.avatar,
        "created_at": comment.created_at
    }
