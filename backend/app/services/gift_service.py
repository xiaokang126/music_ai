from sqlalchemy.orm import Session
from ..models.gift import Gift, WorkGift
from ..models.user import User


def get_all_gifts(db: Session):
    return db.query(Gift).all()


def send_gift(db: Session, work_id: int, sender_id: int, gift_id: int):
    wg = WorkGift(work_id=work_id, sender_id=sender_id, gift_id=gift_id)
    db.add(wg)
    db.commit()
    db.refresh(wg)
    return wg


def get_work_gifts(db: Session, work_id: int):
    gifts = db.query(WorkGift, Gift, User).join(Gift, WorkGift.gift_id == Gift.id).join(
        User, WorkGift.sender_id == User.id
    ).filter(WorkGift.work_id == work_id).order_by(WorkGift.created_at.desc()).limit(50).all()

    result = []
    for wg, gift, user in gifts:
        result.append({
            "id": wg.id, "work_id": wg.work_id, "sender_id": wg.sender_id,
            "gift_id": wg.gift_id, "sender_name": user.username,
            "gift_name": gift.name, "gift_icon": gift.icon,
            "created_at": wg.created_at
        })
    return result
