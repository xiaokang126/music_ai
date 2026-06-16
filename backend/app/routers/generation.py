from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.orm import Session
import json

from ..database import get_db
from ..config import settings
from ..middleware.auth import get_current_user
from ..models.user_model import User
from ..models.generation_model import GenerationSession, GenerationTask
from ..models.timeline_model import MusicTimeline
from ..schemas.generation_schema import (
    GenerationSessionCreate,
    GenerationSessionResponse,
    GenerationTaskItem,
    GenerationTaskUpdate,
)
from ..services.acestep_service import ace_service_available, ace_unavailable_message

router = APIRouter(prefix="/api/generate", tags=["generation"])


def _timeline_segments_from_json(timeline_json: str) -> list:
    timeline_data = json.loads(timeline_json)
    return timeline_data.get("timeline", []) if isinstance(timeline_data, dict) else timeline_data


def _prepare_generation_tasks(db: Session, session: GenerationSession, timeline_json: str) -> list:
    timeline_segments = _timeline_segments_from_json(timeline_json)
    if not isinstance(timeline_segments, list) or len(timeline_segments) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Timeline has no segments",
        )

    db.query(GenerationTask).filter(GenerationTask.session_id == session.id).delete()
    for idx, segment in enumerate(timeline_segments):
        task = GenerationTask(
            session_id=session.id,
            project_id=session.project_id,
            segment_idx=idx,
            prompt=segment.get("caption", "") or segment.get("prompt", "soft background music"),
            status="pending",
        )
        db.add(task)

    session.total_tasks = len(timeline_segments)
    session.completed_tasks = 0
    session.status = "segmenting"
    return timeline_segments


def _latest_generation_error(db: Session, session_id: str) -> str:
    task = db.query(GenerationTask).filter(
        GenerationTask.session_id == session_id,
        GenerationTask.error_msg != "",
    ).order_by(GenerationTask.segment_idx).first()
    return task.error_msg if task else ""


def _mark_generation_failed(db: Session, session: GenerationSession, message: str) -> None:
    session.status = "failed"
    session.completed_tasks = 0
    session.full_audio_path = ""
    tasks = db.query(GenerationTask).filter(GenerationTask.session_id == session.id).all()
    for task in tasks:
        task.status = "failed"
        task.error_msg = message


@router.post("/sessions", response_model=GenerationSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: GenerationSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    timeline = db.query(MusicTimeline).filter(
        MusicTimeline.project_id == data.project_id
    ).first()
    if not timeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeline not found for this project",
        )

    session = GenerationSession(
        project_id=data.project_id,
        user_id=current_user.id,
        status="pending",
        total_tasks=0,
        completed_tasks=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return GenerationSessionResponse(
        id=session.id,
        project_id=session.project_id,
        user_id=session.user_id,
        status=session.status,
        total_tasks=session.total_tasks,
        completed_tasks=session.completed_tasks,
        created_at=session.created_at,
        updated_at=session.updated_at,
        tasks=[],
    )


@router.get("/sessions/{session_id}", response_model=GenerationSessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(GenerationSession).filter(
        GenerationSession.id == session_id,
        GenerationSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    tasks = db.query(GenerationTask).filter(
        GenerationTask.session_id == session_id
    ).order_by(GenerationTask.segment_idx).all()

    return GenerationSessionResponse(
        id=session.id,
        project_id=session.project_id,
        user_id=session.user_id,
        status=session.status,
        total_tasks=session.total_tasks,
        completed_tasks=session.completed_tasks,
        created_at=session.created_at,
        updated_at=session.updated_at,
        tasks=tasks,
    )


@router.post("/sessions/{session_id}/start")
async def start_generation(
    session_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(GenerationSession).filter(
        GenerationSession.id == session_id,
        GenerationSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    timeline = db.query(MusicTimeline).filter(
        MusicTimeline.project_id == session.project_id
    ).first()
    if not timeline or not timeline.timeline_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No timeline data available",
        )

    try:
        _prepare_generation_tasks(db, session, timeline.timeline_json)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timeline JSON",
        )

    db.commit()

    background_tasks.add_task(
        _run_bgm_generation, session_id, session.project_id
    )

    return {"detail": "Generation started", "session_id": session_id}


# ---- Simplified endpoints for PreviewPage ----

@router.get("/by-project/{project_id}")
async def get_by_project(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Check if BGM has been generated for this project."""
    session = db.query(GenerationSession).filter(
        GenerationSession.project_id == project_id
    ).order_by(GenerationSession.created_at.desc()).first()
    if not session:
        return {"audio_url": "", "status": "not_found", "progress": 0}
    if session and session.full_audio_path:
        import os
        if os.path.exists(session.full_audio_path):
            progress = 100 if session.total_tasks == 0 else int(session.completed_tasks / session.total_tasks * 100)
            return {
                "audio_url": f"/api/generate/audio/latest/{project_id}",
                "status": session.status,
                "progress": progress,
                "error_message": "",
            }
    progress = 0 if session.total_tasks == 0 else int(session.completed_tasks / session.total_tasks * 100)
    return {
        "audio_url": "",
        "status": session.status,
        "progress": progress,
        "error_message": _latest_generation_error(db, session.id) if session.status == "failed" else "",
    }


@router.get("/status/{session_id}")
async def generation_status(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(GenerationSession).filter(
        GenerationSession.id == session_id,
        GenerationSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    tasks = db.query(GenerationTask).filter(GenerationTask.session_id == session_id).order_by(GenerationTask.segment_idx).all()
    progress = 0 if session.total_tasks == 0 else int(session.completed_tasks / session.total_tasks * 100)
    return {
        "session_id": session.id,
        "status": session.status,
        "progress": progress,
        "audio_url": f"/api/generate/audio/{session.id}" if session.full_audio_path else "",
        "error_message": _latest_generation_error(db, session.id) if session.status == "failed" else "",
        "segment_statuses": [
            {"segment_idx": t.segment_idx, "status": t.status, "error_msg": t.error_msg}
            for t in tasks
        ],
    }


@router.get("/audio/latest/{project_id}")
async def get_audio(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Serve the latest generated audio file."""
    import os
    session = db.query(GenerationSession).filter(
        GenerationSession.project_id == project_id,
        GenerationSession.status == "completed",
    ).order_by(GenerationSession.created_at.desc()).first()
    if not session or not session.full_audio_path or not os.path.exists(session.full_audio_path):
        raise HTTPException(status_code=404, detail="Audio not found")
    ext = os.path.splitext(session.full_audio_path)[1].lower()
    media_type = "audio/mpeg" if ext == ".mp3" else "audio/flac" if ext == ".flac" else "audio/wav"
    with open(session.full_audio_path, "rb") as f:
        return Response(content=f.read(), media_type=media_type)


@router.get("/public/audio/latest/{project_id}")
async def get_public_audio(project_id: str, db: Session = Depends(get_db)):
    """Serve latest generated audio for browser preview players that cannot send auth headers."""
    import os
    session = db.query(GenerationSession).filter(
        GenerationSession.project_id == project_id,
        GenerationSession.status == "completed",
    ).order_by(GenerationSession.created_at.desc()).first()
    if not session or not session.full_audio_path or not os.path.exists(session.full_audio_path):
        raise HTTPException(status_code=404, detail="Audio not found")
    ext = os.path.splitext(session.full_audio_path)[1].lower()
    media_type = "audio/mpeg" if ext == ".mp3" else "audio/flac" if ext == ".flac" else "audio/wav"
    with open(session.full_audio_path, "rb") as f:
        return Response(content=f.read(), media_type=media_type)


@router.get("/audio/{session_id}")
async def get_audio_by_session(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    import os
    session = db.query(GenerationSession).filter(
        GenerationSession.id == session_id,
        GenerationSession.user_id == current_user.id,
    ).first()
    if not session or not session.full_audio_path or not os.path.exists(session.full_audio_path):
        raise HTTPException(status_code=404, detail="Audio not found")
    ext = os.path.splitext(session.full_audio_path)[1].lower()
    media_type = "audio/mpeg" if ext == ".mp3" else "audio/flac" if ext == ".flac" else "audio/wav"
    with open(session.full_audio_path, "rb") as f:
        return Response(content=f.read(), media_type=media_type)


@router.get("/acestep/health")
async def acestep_health(current_user: User = Depends(get_current_user)):
    from ..services.acestep_service import ace_service_available
    available = await ace_service_available()
    return {
        "available": available,
        "mode": "ace_only",
        "fallback_enabled": False,
        "api_url": settings.ACESTEP_API_URL,
        "error_message": "" if available else ace_unavailable_message(),
    }


# ---- Core BGM generation endpoint (uses ACE-Step) ----

@router.post("/bgm")
async def generate_bgm(
    body: dict,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start ACE-Step BGM generation for a project's timeline."""
    project_id = body.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="Missing project_id")

    tl = db.query(MusicTimeline).filter(MusicTimeline.project_id == project_id).first()
    if not tl:
        raise HTTPException(status_code=400, detail="请先生成 Music Timeline")

    # Reuse only an active session; completed/failed sessions remain as history.
    existing_session = db.query(GenerationSession).filter(
        GenerationSession.project_id == project_id
    ).order_by(GenerationSession.created_at.desc()).first()

    if existing_session and existing_session.status in {"pending", "segmenting", "generating", "started"}:
        session = existing_session
        session.status = "segmenting"
        session.full_audio_path = ""
        session.completed_tasks = 0
        db.commit()
    else:
        session = GenerationSession(
            project_id=project_id, 
            user_id=current_user.id,
            status="segmenting"
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    try:
        _prepare_generation_tasks(db, session, tl.timeline_json)
        db.commit()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid timeline JSON")

    if not await ace_service_available():
        message = ace_unavailable_message()
        _mark_generation_failed(db, session, message)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": message,
                "project_id": project_id,
                "strategy": "ace_only_no_fallback",
                "api_url": settings.ACESTEP_API_URL,
            },
        )

    background_tasks.add_task(_run_bgm_generation, session.id, project_id)
    return {"session_id": session.id, "status": "started"}


async def _run_bgm_generation(session_id: str, project_id: str):
    """Background task: generate BGM with ACE-Step."""
    from ..database import SessionLocal
    from ..services.acestep_service import generate_bgm_for_timeline

    db = SessionLocal()
    try:
        tl = db.query(MusicTimeline).filter(MusicTimeline.project_id == project_id).first()
        if not tl or not tl.timeline_json:
            return
        timeline_data = json.loads(tl.timeline_json)

        session = db.query(GenerationSession).filter(GenerationSession.id == session_id).first()
        if not session:
            return

        try:
            result = await generate_bgm_for_timeline(timeline_data, project_id)
            if result.get("success"):
                session.status = "completed"
                session.full_audio_path = result.get("audio_path", "")
                session.total_tasks = result.get("total_segments", session.total_tasks)
                session.completed_tasks = result.get("segment_count", session.completed_tasks)
                tasks = db.query(GenerationTask).filter(
                    GenerationTask.session_id == session_id
                ).order_by(GenerationTask.segment_idx).all()
                for idx, task in enumerate(tasks):
                    task.status = "completed" if idx < session.completed_tasks else "failed"
            else:
                _mark_generation_failed(db, session, result.get("error", "ACE 生成失败，但没有返回具体错误"))
        except Exception as exc:
            message = str(exc) or "ACE 生成失败，但没有返回具体错误"
            if "使用 ACE 调用失败" not in message:
                message = f"使用 ACE 调用失败：{message}。当前项目只允许使用 ACE 生成音频，未换用本地合成或其他降级策略。"
            _mark_generation_failed(db, session, message)
        db.commit()
    finally:
        db.close()
