from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.music_work import WorkCreate, WorkListResponse
from ..middleware.auth import get_current_user
from ..services import work_service

router = APIRouter(prefix="/api/works", tags=["works"])


@router.get("")
def list_works(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("latest"),
    mood: str = Query(""),
    search: str = Query(""),
    db: Session = Depends(get_db)
):
    works, total = work_service.get_works(db, page, page_size, sort, mood, search)
    return {"works": works, "total": total, "page": page, "page_size": page_size}


@router.post("")
def create_work(data: WorkCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    resp = work_service.create_work(
        db, user.id, data.title, data.mood_tag, data.params_json,
        data.reply_to_work_id, data.description
    )
    return resp


@router.get("/{work_id}")
def get_work(work_id: int, db: Session = Depends(get_db)):
    detail = work_service.get_work_detail(db, work_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Work not found")
    return detail


@router.post("/{work_id}/reply")
def reply_work(work_id: int, data: WorkCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    data.reply_to_work_id = work_id
    return create_work(data, db, user)


@router.post("/{work_id}/like")
def like_work(work_id: int, db: Session = Depends(get_db)):
    result = work_service.like_work(db, work_id)
    if not result:
        raise HTTPException(status_code=404, detail="Work not found")
    return result


@router.put("/{work_id}")
def update_work(work_id: int, data: WorkCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    resp = work_service.update_work(db, work_id, user.id, data.title, data.description)
    if not resp:
        raise HTTPException(status_code=404, detail="Work not found")
    return resp


@router.delete("/{work_id}")
def delete_work(work_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ok = work_service.delete_work(db, work_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Work not found")
    return {"message": "deleted"}
