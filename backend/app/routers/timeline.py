import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..middleware.auth import get_current_user
from ..models.user_model import User
from ..models.video_model import VideoProject
from ..models.timeline_model import MusicTimeline
from ..schemas.timeline_schema import (
    TimelineGenerateRequest,
    TimelineRestyleRequest,
    TimelineUpdateRequest,
    TimelineResponse,
)
from ..services.llm_service import generate_timeline as llm_generate

router = APIRouter(prefix="/api/timeline", tags=["timeline"])
logger = logging.getLogger("musecut.timeline")


def _timeline_error_detail(stage: str, exc: Exception, project: VideoProject | None = None, project_id: str = "") -> dict:
    return {
        "message": "生成 Music Timeline 失败",
        "stage": stage,
        "project_id": project_id or (project.id if project else ""),
        "video_path": project.video_path if project else "",
        "project_status": project.status if project else "",
        "video_profile_length": len(project.video_profile or "") if project else 0,
        "error_type": exc.__class__.__name__,
        "error": str(exc),
        "hint": "请把本提示中的 request_id 和 stage 发给开发者；服务端完整堆栈记录在 backend/logs/musecut.log",
    }


@router.post("/generate", response_model=TimelineResponse)
async def generate(body: TimelineGenerateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(VideoProject).filter(VideoProject.id == body.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    stage = "build_profile"
    try:
        if not project.video_profile:
            # Auto-build profile if missing
            from ..services.video_analyzer import detect_scene_changes
            from ..services.video_profile import build_video_profile
            sc = detect_scene_changes(project.video_path)
            kp = json.loads(project.key_points_json) if project.key_points_json else []
            vr = json.loads(project.voice_regions_json) if project.voice_regions_json else []
            ce = json.loads(project.caption_events_json) if project.caption_events_json else []
            profile = build_video_profile(project, sc, kp, vr, ce)
            project.video_profile = json.dumps(profile, ensure_ascii=False)
            project.status = "profiled"
            db.commit()

        stage = "parse_video_profile"
        video_profile = json.loads(project.video_profile)

        stage = "llm_generate"
        timeline_data = llm_generate(video_profile, body.style)

        stage = "upsert_timeline"
        existing = db.query(MusicTimeline).filter(MusicTimeline.project_id == body.project_id).first()
        if existing:
            existing.style = timeline_data.get("style", body.style)
            existing.bpm = str(timeline_data.get("bpm", 82))
            existing.key = timeline_data.get("key", "C_major")
            existing.duration = float(timeline_data.get("duration", 0))
            existing.global_caption = timeline_data.get("global_caption", "")
            existing.timeline_json = json.dumps(timeline_data, ensure_ascii=False)
            db.commit()
            db.refresh(existing)
            return existing

        tl = MusicTimeline(
            project_id=body.project_id,
            style=timeline_data.get("style", body.style),
            bpm=str(timeline_data.get("bpm", 82)),
            key=timeline_data.get("key", "C_major"),
            duration=float(timeline_data.get("duration", 0)),
            global_caption=timeline_data.get("global_caption", ""),
            timeline_json=json.dumps(timeline_data, ensure_ascii=False),
        )
        db.add(tl)
        db.commit()
        db.refresh(tl)
        return tl
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Timeline generation failed stage=%s project_id=%s user_id=%s style=%s",
            stage,
            body.project_id,
            user.id,
            body.style,
        )
        raise HTTPException(status_code=500, detail=_timeline_error_detail(stage, exc, project, body.project_id))


@router.get("/by-project/{project_id}", response_model=TimelineResponse)
async def get_by_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tl = db.query(MusicTimeline).filter(MusicTimeline.project_id == project_id).first()
    if not tl:
        raise HTTPException(status_code=404, detail="Timeline 不存在")
    return tl


@router.put("/{timeline_id}", response_model=TimelineResponse)
async def update(timeline_id: str, body: TimelineUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tl = db.query(MusicTimeline).filter(MusicTimeline.id == timeline_id).first()
    if not tl:
        raise HTTPException(status_code=404, detail="Timeline 不存在")
    if body.style is not None:
        tl.style = body.style
    if body.bpm is not None:
        tl.bpm = str(body.bpm)
    if body.key is not None:
        tl.key = body.key
    if body.timeline_json is not None:
        tl.timeline_json = body.timeline_json
    if body.global_caption is not None:
        tl.global_caption = body.global_caption
    db.commit()
    db.refresh(tl)
    return tl


@router.post("/{timeline_id}/restyle", response_model=TimelineResponse)
async def restyle(timeline_id: str, body: TimelineRestyleRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tl = db.query(MusicTimeline).filter(MusicTimeline.id == timeline_id).first()
    if not tl:
        raise HTTPException(status_code=404, detail="Timeline 不存在")
    project = db.query(VideoProject).filter(VideoProject.id == tl.project_id).first()
    if not project or not project.video_profile:
        raise HTTPException(status_code=400, detail="视频信息不完整")
    stage = "restyle_parse_profile"
    try:
        video_profile = json.loads(project.video_profile)
        stage = "restyle_llm_generate"
        timeline_data = llm_generate(video_profile, body.new_style)
        stage = "restyle_update_timeline"
        tl.style = timeline_data.get("style", body.new_style)
        tl.bpm = str(timeline_data.get("bpm", 82))
        tl.key = timeline_data.get("key", "C_major")
        tl.duration = float(timeline_data.get("duration", 0))
        tl.global_caption = timeline_data.get("global_caption", "")
        tl.timeline_json = json.dumps(timeline_data, ensure_ascii=False)
        db.commit()
        db.refresh(tl)
        return tl
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Timeline restyle failed stage=%s timeline_id=%s project_id=%s user_id=%s style=%s",
            stage,
            timeline_id,
            tl.project_id,
            user.id,
            body.new_style,
        )
        raise HTTPException(status_code=500, detail=_timeline_error_detail(stage, exc, project, tl.project_id))
