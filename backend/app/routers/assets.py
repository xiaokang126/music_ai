"""User-provided assets: SFX uploads + Inspiration library."""
import os
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..config import settings
from ..middleware.auth import get_current_user, get_optional_user
from ..models.user_model import User
from ..models.user_asset_model import UserSFX, UserInspiration

router = APIRouter(prefix="/api/assets", tags=["assets"])

# ─── SFX Upload ───────────────────────────────────────────

@router.post("/sfx/upload")
async def upload_sfx(
    file: UploadFile = File(...),
    name: str = Form(""),
    sfx_type: str = Form("custom"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="请上传音频文件 (wav/mp3)")

    sfx_dir = os.path.join(settings.UPLOAD_DIR, "sfx")
    os.makedirs(sfx_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] or ".wav"
    filename = f"{file_id}{ext}"
    filepath = os.path.join(sfx_dir, filename)

    file.file.seek(0)
    content = file.file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    sfx = UserSFX(
        id=file_id,
        user_id=current_user.id,
        name=name or os.path.splitext(file.filename)[0],
        sfx_type=sfx_type,
        filename=file.filename,
        file_path=filepath,
    )
    db.add(sfx)
    db.commit()
    db.refresh(sfx)
    return {
        "id": sfx.id, "name": sfx.name, "sfx_type": sfx.sfx_type,
        "url": f"/api/assets/sfx/{sfx.id}/play",
    }


@router.get("/sfx")
async def list_sfx(
    sfx_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(UserSFX).filter(UserSFX.user_id == current_user.id)
    if sfx_type:
        q = q.filter(UserSFX.sfx_type == sfx_type)
    sfxs = q.order_by(UserSFX.created_at.desc()).all()
    return [{
        "id": s.id, "name": s.name, "sfx_type": s.sfx_type,
        "url": f"/api/assets/sfx/{s.id}/play",
        "created_at": str(s.created_at) if s.created_at else "",
    } for s in sfxs]


@router.get("/sfx/{sfx_id}/play")
async def play_sfx(sfx_id: str, db: Session = Depends(get_db)):
    sfx = db.query(UserSFX).filter(UserSFX.id == sfx_id).first()
    if not sfx or not os.path.exists(sfx.file_path):
        raise HTTPException(status_code=404, detail="音效文件不存在")
    ext = os.path.splitext(sfx.file_path)[1].lower()
    media = "audio/wav" if ext == ".wav" else "audio/mpeg"
    with open(sfx.file_path, "rb") as f:
        return Response(content=f.read(), media_type=media)


@router.delete("/sfx/{sfx_id}")
async def delete_sfx(
    sfx_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sfx = db.query(UserSFX).filter(UserSFX.id == sfx_id, UserSFX.user_id == current_user.id).first()
    if not sfx:
        raise HTTPException(status_code=404, detail="音效不存在")
    if os.path.exists(sfx.file_path):
        os.remove(sfx.file_path)
    db.delete(sfx)
    db.commit()
    return {"detail": "已删除"}


# ─── Inspiration Library ──────────────────────────────────

@router.post("/inspiration")
async def create_inspiration(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    insp = UserInspiration(
        user_id=current_user.id,
        title=body.get("title", ""),
        description=body.get("description", ""),
        theme=body.get("theme", ""),
        emotion=body.get("emotion", "warm"),
        reference_url=body.get("reference_url", ""),
        tags=json.dumps(body.get("tags", []), ensure_ascii=False),
    )
    db.add(insp)
    db.commit()
    db.refresh(insp)
    return _insp_to_dict(insp)


@router.get("/inspiration")
async def list_inspirations(
    theme: Optional[str] = Query(None),
    emotion: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(UserInspiration)
    if theme:
        q = q.filter(UserInspiration.theme == theme)
    if emotion:
        q = q.filter(UserInspiration.emotion == emotion)
    total = q.count()
    items = q.order_by(UserInspiration.likes_count.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_insp_to_dict(i) for i in items],
        "total": total, "page": page, "page_size": page_size,
    }


@router.post("/inspiration/{insp_id}/like")
async def like_inspiration(insp_id: str, db: Session = Depends(get_db)):
    insp = db.query(UserInspiration).filter(UserInspiration.id == insp_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="灵感不存在")
    insp.likes_count += 1
    db.commit()
    return {"likes_count": insp.likes_count}


@router.delete("/inspiration/{insp_id}")
async def delete_inspiration(
    insp_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    insp = db.query(UserInspiration).filter(UserInspiration.id == insp_id, UserInspiration.user_id == current_user.id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="灵感不存在")
    db.delete(insp)
    db.commit()
    return {"detail": "已删除"}


def _insp_to_dict(i: UserInspiration) -> dict:
    return {
        "id": i.id, "user_id": i.user_id,
        "title": i.title, "description": i.description,
        "theme": i.theme, "emotion": i.emotion,
        "reference_url": i.reference_url,
        "tags": json.loads(i.tags) if i.tags else [],
        "likes_count": i.likes_count,
        "created_at": str(i.created_at) if i.created_at else "",
    }
