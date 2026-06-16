import os
import json
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from ..middleware.auth import get_current_user
from ..models.user_model import User
from ..models.video_model import VideoProject
from ..models.timeline_model import MusicTimeline
from ..models.generation_model import GenerationSession
from ..models.export_model import ExportTask
from ..models.user_asset_model import UserSFX
from ..services.exporter import render_mixed_audio, render_video_with_mixed_audio

router = APIRouter(prefix="/api/export", tags=["export"])
logger = logging.getLogger("musecut.export")
optional_bearer = HTTPBearer(auto_error=False)


@router.post("/audio")
async def export_audio(body: dict, background_tasks: BackgroundTasks,
                 current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project_id = body.get("project_id")
    fmt = body.get("format", "mp4")
    if fmt not in ("mp4", "wav", "flac", "mp3", "json"):
        raise HTTPException(status_code=400, detail="不支持的格式")

    project = db.query(VideoProject).filter(
        VideoProject.id == project_id,
        VideoProject.user_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在或无权导出")

    task = ExportTask(project_id=project_id, format=fmt, status="processing")
    db.add(task)
    db.commit()
    db.refresh(task)
    background_tasks.add_task(_do_export, task.id, project_id, fmt)
    return {"export_id": task.id, "status": "processing"}


@router.get("/status/{export_id}")
async def export_status(export_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(ExportTask).filter(ExportTask.id == export_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="导出任务不存在")
    message = ""
    if task.status == "failed":
        message = task.error_msg or "导出失败，完整原因已记录在 backend/logs/musecut.log"
    return {"export_id": task.id, "status": task.status, "file_url": task.file_url or None, "message": message}


def _build_download_token(export_id: str, user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload = {
        "purpose": "export_download",
        "export_id": export_id,
        "user_id": user_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _decode_download_token(token: str, export_id: str) -> str:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="下载链接已失效，请重新点击导出下载")
    if payload.get("purpose") != "export_download" or payload.get("export_id") != export_id:
        raise HTTPException(status_code=401, detail="下载链接与导出任务不匹配")
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="下载链接缺少用户信息")
    return user_id


def _get_authorized_task(db: Session, export_id: str, user_id: str) -> ExportTask:
    task = db.query(ExportTask).filter(ExportTask.id == export_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    project = db.query(VideoProject).filter(VideoProject.id == task.project_id).first()
    if not project or project.user_id != user_id:
        raise HTTPException(status_code=404, detail="任务不存在或无权下载")
    return task


def _download_response(task: ExportTask) -> Response:
    if task.status != "completed" or not task.file_path or not os.path.exists(task.file_path):
        raise HTTPException(status_code=400, detail="文件尚未就绪")
    media = (
        "video/mp4" if task.format == "mp4"
        else "application/json" if task.format == "json"
        else "audio/mpeg" if task.format == "mp3"
        else f"audio/{task.format}"
    )
    headers = {
        "Content-Disposition": f'attachment; filename="musecut_export.{task.format}"',
        "Content-Length": str(os.path.getsize(task.file_path)),
    }
    with open(task.file_path, "rb") as f:
        return Response(content=f.read(), media_type=media, headers=headers)


@router.get("/download-token/{export_id}")
async def export_download_token(export_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = _get_authorized_task(db, export_id, current_user.id)
    if task.status != "completed" or not task.file_path or not os.path.exists(task.file_path):
        raise HTTPException(status_code=400, detail="文件尚未就绪")
    token = _build_download_token(export_id, current_user.id)
    return {"download_url": f"/api/export/download/{export_id}?token={token}", "expires_in_seconds": 600}


@router.get("/download/{export_id}")
async def download_export(
    export_id: str,
    token: str | None = Query(default=None),
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: Session = Depends(get_db),
):
    if token:
        user_id = _decode_download_token(token, export_id)
    elif credentials:
        try:
            payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("user_id")
        except JWTError:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    else:
        raise HTTPException(status_code=401, detail="Not authenticated")

    task = _get_authorized_task(db, export_id, user_id)
    return _download_response(task)


async def _do_export(export_id: str, project_id: str, fmt: str):
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        task = db.query(ExportTask).filter(ExportTask.id == export_id).first()
        if not task:
            return
        os.makedirs(settings.EXPORT_DIR, exist_ok=True)
        output_path = os.path.join(settings.EXPORT_DIR, f"{project_id}_export.{fmt}")
        project = db.query(VideoProject).filter(VideoProject.id == project_id).first()

        if fmt == "json":
            tl = db.query(MusicTimeline).filter(MusicTimeline.project_id == project_id).first()
            if tl:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(tl.timeline_json)
                task.file_path = output_path
                task.file_url = f"/api/export/download/{export_id}"
                task.status = "completed"
            else:
                logger.error("Export failed export_id=%s project_id=%s fmt=%s reason=timeline_missing", export_id, project_id, fmt)
                task.status = "failed"
                task.error_msg = "导出失败：没有找到 Music Timeline，无法导出 JSON 方案。"
        else:
            tl = db.query(MusicTimeline).filter(MusicTimeline.project_id == project_id).first()
            if not tl or not tl.timeline_json:
                logger.error("Export failed export_id=%s project_id=%s fmt=%s reason=timeline_missing_or_empty", export_id, project_id, fmt)
                task.status = "failed"
                task.error_msg = "导出失败：没有找到 Music Timeline，请先完成声音编排。"
                db.commit()
                return
            try:
                timeline_data = json.loads(tl.timeline_json)
            except json.JSONDecodeError as exc:
                logger.exception("Export failed export_id=%s project_id=%s fmt=%s reason=timeline_json_invalid error=%s", export_id, project_id, fmt, str(exc))
                task.status = "failed"
                task.error_msg = f"导出失败：Music Timeline JSON 无法解析，错误：{exc}"
                db.commit()
                return

            session = db.query(GenerationSession).filter(
                GenerationSession.project_id == project_id,
                GenerationSession.status == "completed",
            ).order_by(GenerationSession.created_at.desc()).first()

            bgm_path = session.full_audio_path if session and session.full_audio_path else None
            if not bgm_path or not os.path.exists(bgm_path):
                message = (
                    "导出失败：没有找到 ACE 生成的 BGM 音频。当前项目只允许使用 ACE 生成音频，"
                    "未换用本地合成或其他降级策略。请先确认 ACE-Step 服务可用并重新生成 BGM。"
                )
                logger.error("Export failed export_id=%s project_id=%s fmt=%s reason=ace_bgm_missing", export_id, project_id, fmt)
                task.status = "failed"
                task.error_msg = message
                db.commit()
                return
            custom_sfx_paths = {}
            if project:
                custom_sfx_paths = {
                    f"user:{sfx.id}": sfx.file_path
                    for sfx in db.query(UserSFX).filter(UserSFX.user_id == project.user_id).all()
                }
            try:
                if fmt == "mp4":
                    if not project or not project.video_path or not os.path.exists(project.video_path):
                        logger.error("Export failed export_id=%s project_id=%s fmt=%s reason=video_missing", export_id, project_id, fmt)
                        task.status = "failed"
                        task.error_msg = "导出失败：原始视频文件不存在，无法合成成片。"
                        db.commit()
                        return
                    render_video_with_mixed_audio(timeline_data, bgm_path, project.video_path, output_path, custom_sfx_paths)
                else:
                    render_mixed_audio(timeline_data, bgm_path, output_path, fmt, custom_sfx_paths)
                if os.path.exists(output_path):
                    task.file_path = output_path
                    task.file_url = f"/api/export/download/{export_id}"
                    task.status = "completed"
                else:
                    logger.error("Export failed export_id=%s project_id=%s fmt=%s reason=output_missing output_path=%s", export_id, project_id, fmt, output_path)
                    task.status = "failed"
                    task.error_msg = "导出失败：渲染结束后没有生成可下载文件。"
            except Exception as exc:
                logger.exception("Export failed export_id=%s project_id=%s fmt=%s reason=render_exception error=%s", export_id, project_id, fmt, str(exc))
                task.status = "failed"
                task.error_msg = f"导出失败：{exc}"
        db.commit()
    finally:
        db.close()
