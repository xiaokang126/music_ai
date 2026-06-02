from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from ..models.music_work import MusicWork
from ..models.user import User
from ..models.comment import Comment
from ..models.gift import WorkGift


def create_work(db: Session, user_id: int, title: str, mood_tag: str, params_json: str,
                reply_to_work_id: int = None, description: str = ""):
    work = MusicWork(
        user_id=user_id, title=title, mood_tag=mood_tag,
        params_json=params_json, reply_to_work_id=reply_to_work_id,
        description=description
    )
    db.add(work)
    db.commit()
    db.refresh(work)
    return _to_response(db, work)


def get_works(db: Session, page: int = 1, page_size: int = 20,
              sort: str = "latest", mood: str = "", search: str = ""):
    query = db.query(MusicWork).filter(MusicWork.is_public == True)
    if mood:
        query = query.filter(MusicWork.mood_tag == mood)
    if search:
        query = query.filter(MusicWork.title.contains(search) | MusicWork.description.contains(search))
    if sort == "hot":
        query = query.order_by(desc(MusicWork.likes_count), desc(MusicWork.created_at))
    else:
        query = query.order_by(desc(MusicWork.created_at))

    total = query.count()
    works = query.offset((page - 1) * page_size).limit(page_size).all()
    return [_to_response(db, w) for w in works], total


def get_work_detail(db: Session, work_id: int):
    work = db.query(MusicWork).filter(MusicWork.id == work_id).first()
    if not work:
        return None
    result = _to_response(db, work)
    replies = db.query(MusicWork).filter(MusicWork.reply_to_work_id == work_id).order_by(MusicWork.created_at).all()
    result["replies"] = [_to_response(db, r) for r in replies]
    return result


def get_user_works(db: Session, user_id: int, page: int = 1, page_size: int = 20):
    query = db.query(MusicWork).filter(MusicWork.user_id == user_id).order_by(desc(MusicWork.created_at))
    total = query.count()
    works = query.offset((page - 1) * page_size).limit(page_size).all()
    return [_to_response(db, w) for w in works], total


def like_work(db: Session, work_id: int):
    work = db.query(MusicWork).filter(MusicWork.id == work_id).first()
    if work:
        work.likes_count += 1
        db.commit()
        return {"likes_count": work.likes_count}
    return None


def update_work(db: Session, work_id: int, user_id: int, title: str = None, description: str = None):
    work = db.query(MusicWork).filter(MusicWork.id == work_id, MusicWork.user_id == user_id).first()
    if not work:
        return None
    if title:
        work.title = title
    if description is not None:
        work.description = description
    db.commit()
    return _to_response(db, work)


def delete_work(db: Session, work_id: int, user_id: int):
    work = db.query(MusicWork).filter(MusicWork.id == work_id, MusicWork.user_id == user_id).first()
    if not work:
        return False
    db.delete(work)
    db.commit()
    return True


def _to_response(db: Session, work: MusicWork):
    user = db.query(User).filter(User.id == work.user_id).first()
    reply_count = db.query(func.count(MusicWork.id)).filter(MusicWork.reply_to_work_id == work.id).scalar()
    gift_count = db.query(func.count(WorkGift.id)).filter(WorkGift.work_id == work.id).scalar()
    comment_count = db.query(func.count(Comment.id)).filter(Comment.work_id == work.id).scalar()
    return {
        "id": work.id, "user_id": work.user_id, "title": work.title,
        "mood_tag": work.mood_tag, "params_json": work.params_json,
        "reply_to_work_id": work.reply_to_work_id, "is_public": work.is_public,
        "likes_count": work.likes_count, "description": work.description,
        "created_at": work.created_at,
        "username": user.username if user else "",
        "avatar": user.avatar if user else "",
        "reply_count": reply_count or 0,
        "gift_count": gift_count or 0,
        "comment_count": comment_count or 0,
    }
