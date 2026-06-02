from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.gift import GiftSendRequest
from ..middleware.auth import get_current_user
from ..services.gift_service import get_all_gifts, send_gift, get_work_gifts

router = APIRouter(prefix="/api", tags=["gifts"])


@router.get("/gifts")
def list_gifts(db: Session = Depends(get_db)):
    gifts = get_all_gifts(db)
    return [{"id": g.id, "name": g.name, "icon": g.icon, "type": g.type} for g in gifts]


@router.get("/works/{work_id}/gifts")
def list_work_gifts(work_id: int, db: Session = Depends(get_db)):
    return get_work_gifts(db, work_id)


@router.post("/works/{work_id}/gifts")
def send_work_gift(work_id: int, data: GiftSendRequest, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    wg = send_gift(db, work_id, user.id, data.gift_id)
    return {"message": "gift sent"}
