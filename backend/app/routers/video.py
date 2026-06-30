import os
import json
import uuid
from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from ..middleware.auth import get_current_user, get_optional_user
from ..models.user_model import User
from ..models.video_model import VideoProject
from ..models.timeline_model import MusicTimeline
from ..models.generation_model import GenerationSession, GenerationTask
from ..models.export_model import ExportTask
from ..models.community_model import CommunityPost, Comment, Like, Collect
from ..schemas.video_schema import (
    KeyPointsRequest,
    VideoProjectResponse,
    VideoProjectListResponse,
)
from ..services.video_analyzer import extract_metadata, detect_scene_changes
from ..services.profile_builder import build_profile_for_project, loads_json

router = APIRouter(prefix="/api/video", tags=["video"])


def _profile_duration(profile: dict) -> float:
    metadata = profile.get("metadata") or {}
    try:
        return max(1.0, float(metadata.get("duration") or profile.get("duration") or 3.0))
    except (TypeError, ValueError):
        return 3.0


def _text_music_intent(text: str) -> tuple[str, float]:
    compact = text.lower()
    keyword_sets = [
        (("燃", "高能", "热血", "兴奋", "冲刺", "快节奏", "节奏强", "运动"), ("energetic", 0.76)),
        (("紧张", "冲突", "压迫", "危险", "严肃", "强烈"), ("intense", 0.72)),
        (("开心", "快乐", "明亮", "轻快", "可爱", "活泼"), ("happy", 0.62)),
        (("悲伤", "难过", "失落", "遗憾", "告别", "想念"), ("sad", 0.5)),
        (("怀旧", "回忆", "毕业", "校园", "朋友", "青春"), ("nostalgic", 0.55)),
        (("神秘", "悬疑", "夜晚", "未知"), ("mysterious", 0.55)),
        (("温暖", "温柔", "治愈", "陪伴", "家庭"), ("warm", 0.5)),
        (("平静", "安静", "克制", "舒缓", "柔和"), ("calm", 0.38)),
    ]
    for keywords, result in keyword_sets:
        if any(word in compact for word in keywords):
            return result
    return "warm", 0.48


def _rebuild_arc_from_semantic_text(profile: dict, semantic: dict) -> list[dict]:
    duration = _profile_duration(profile)
    current_arc = semantic.get("emotional_arc") if isinstance(semantic.get("emotional_arc"), list) else []
    base_text = f"{semantic.get('story_summary', '')} {semantic.get('music_director_brief', '')}"
    emotion, base_energy = _text_music_intent(base_text)
    compact = base_text.lower()
    wants_lift = any(word in compact for word in ("结尾抬起", "结尾提升", "最后抬起", "收束", "升起", "推高", "高潮"))
    wants_restrained = any(word in compact for word in ("克制", "不要抢", "轻轻", "柔和", "低密度", "人声"))

    if len(current_arc) >= 3:
        boundaries = [float(current_arc[0].get("start", 0) or 0)]
        for item in current_arc[:3]:
            try:
                boundaries.append(float(item.get("end") or duration))
            except (TypeError, ValueError):
                boundaries.append(duration)
        boundaries[0] = 0.0
        boundaries[-1] = duration
    else:
        boundaries = [0.0, round(duration / 3, 2), round(duration * 2 / 3, 2), duration]

    arc: list[dict] = []
    for idx in range(3):
        item = current_arc[idx] if idx < len(current_arc) and isinstance(current_arc[idx], dict) else {}
        seg_energy = base_energy
        seg_emotion = emotion
        if idx == 0 and wants_restrained:
            seg_energy = min(seg_energy, 0.38)
            seg_emotion = "calm" if emotion in {"warm", "nostalgic", "happy"} else emotion
        if idx == 1:
            seg_energy = min(0.82, seg_energy + 0.08)
        if idx == 2 and wants_lift:
            seg_energy = min(0.86, max(seg_energy + 0.16, 0.58))
            if seg_emotion in {"calm", "sad"}:
                seg_emotion = "warm"
        elif idx == 2:
            seg_energy = max(0.32, seg_energy - 0.05)

        arc.append({
            "start": round(max(0.0, boundaries[idx]), 2),
            "end": round(max(boundaries[idx] + 0.2, min(duration, boundaries[idx + 1])), 2),
            "visual": item.get("visual") or f"用户修正理解后的第 {idx + 1} 段",
            "emotion": seg_emotion,
            "energy": round(seg_energy, 2),
            "music_intent": (
                semantic.get("music_director_brief")
                or item.get("music_intent")
                or "根据用户修正后的故事理解重新组织完整连续配乐。"
            ),
        })
    arc[-1]["end"] = round(duration, 2)
    return arc


def _video_file_response(path: str, request: Request, media_type: str = "video/mp4"):
    size = os.path.getsize(path)
    headers = {"Accept-Ranges": "bytes"}
    range_header = request.headers.get("range")
    if not range_header:
        return FileResponse(path, media_type=media_type, headers=headers)

    try:
        unit, raw_range = range_header.split("=", 1)
        if unit.strip().lower() != "bytes":
            raise ValueError("unsupported range unit")
        start_s, end_s = raw_range.split("-", 1)
        if start_s:
            start = int(start_s)
            end = int(end_s) if end_s else size - 1
        else:
            suffix = int(end_s)
            start = max(0, size - suffix)
            end = size - 1
        start = max(0, min(start, size - 1))
        end = max(start, min(end, size - 1))
    except Exception:
        raise HTTPException(status_code=416, detail="Invalid range request")

    headers.update({
        "Content-Range": f"bytes {start}-{end}/{size}",
        "Content-Length": str(end - start + 1),
    })
    with open(path, "rb") as f:
        f.seek(start)
        content = f.read(end - start + 1)
    return Response(
        content=content,
        status_code=206,
        media_type=media_type,
        headers=headers,
    )


@router.post("/upload", response_model=VideoProjectResponse)
async def upload(
    video: UploadFile = File(...),
    video_type: str = Form("campus_memory"),
    user_description: str = Form(""),
    enable_ocr: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not video.filename:
        raise HTTPException(status_code=400, detail="请上传有效的视频文件")
    
    # 检查文件扩展名或MIME类型
    allowed_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'}
    file_ext = os.path.splitext(video.filename)[1].lower()
    is_valid_type = (video.content_type and video.content_type.startswith("video/")) or (file_ext in allowed_extensions)
    
    if not is_valid_type:
        raise HTTPException(status_code=400, detail="请上传有效的视频文件（支持 MP4, MOV, AVI, MKV, WebM 等格式）")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(video.filename)[1] or ".mp4"
    filename = f"{file_id}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    video.file.seek(0)
    content = video.file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Extract metadata
    metadata = await extract_metadata(filepath)
    metadata["semantic_options"] = {
        "mode": "balanced",
        "ocr_enabled": bool(enable_ocr),
    }

    project = VideoProject(
        id=file_id,
        user_id=current_user.id,
        title=os.path.splitext(video.filename)[0],
        video_filename=video.filename,
        video_path=filepath,
        video_type=video_type,
        user_description=user_description,
        status="uploaded",
        metadata_json=json.dumps(metadata, ensure_ascii=False),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=VideoProjectListResponse)
async def list_projects(
    page: int = 1,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(VideoProject).filter(VideoProject.user_id == current_user.id)
    total = q.count()
    projects = q.order_by(VideoProject.created_at.desc()).offset((page-1)*20).limit(20).all()
    responses = []
    for project in projects:
        item = VideoProjectResponse.model_validate(project)
        if project.metadata_json:
            try:
                item.duration = json.loads(project.metadata_json).get("duration", 0)
            except json.JSONDecodeError:
                item.duration = 0
        responses.append(item)
    return VideoProjectListResponse(
        projects=responses,
        total=total, page=page, page_size=20,
    )


@router.get("/{project_id}", response_model=VideoProjectResponse)
async def get_project(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    r = VideoProjectResponse.model_validate(p)
    if p.metadata_json:
        r.duration = json.loads(p.metadata_json).get("duration", 0)
    return r


@router.get("/{project_id}/preview")
async def preview_video(project_id: str, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not p or not os.path.exists(p.video_path):
        raise HTTPException(status_code=404, detail="视频不存在")
    return _video_file_response(p.video_path, request)


@router.get("/public/{project_id}/preview")
async def public_preview_video(project_id: str, request: Request, db: Session = Depends(get_db)):
    """Public video preview - no auth required, for community embedding."""
    p = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not p or not os.path.exists(p.video_path):
        raise HTTPException(status_code=404, detail="视频不存在")
    return _video_file_response(p.video_path, request)


@router.get("/{project_id}/scene-changes")
async def get_scene_changes(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return detect_scene_changes(p.video_path)


@router.get("/{project_id}/profile")
async def get_profile(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")

    # If already profiled, return cached
    if p.video_profile:
        return json.loads(p.video_profile)

    profile = build_profile_for_project(p)
    p.video_profile = json.dumps(profile, ensure_ascii=False)
    p.status = "profiled"
    db.commit()
    return profile


@router.put("/{project_id}/semantic")
async def update_semantic_profile(
    project_id: str,
    body: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.query(VideoProject).filter(VideoProject.id == project_id, VideoProject.user_id == current_user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")

    profile = loads_json(p.video_profile, None) if p.video_profile else None
    if not isinstance(profile, dict):
        profile = build_profile_for_project(p)

    semantic = profile.get("semantic_understanding") or {}
    text_changed = False
    if "story_summary" in body:
        semantic["story_summary"] = str(body.get("story_summary") or "").strip()
        text_changed = True
    if "music_director_brief" in body:
        semantic["music_director_brief"] = str(body.get("music_director_brief") or "").strip()
        text_changed = True
    if isinstance(body.get("emotional_arc"), list):
        semantic["emotional_arc"] = body["emotional_arc"]
    if isinstance(body.get("caption_texts"), list):
        semantic["caption_texts"] = body["caption_texts"]
    elif text_changed:
        semantic["emotional_arc"] = _rebuild_arc_from_semantic_text(profile, semantic)
    semantic["user_edited"] = True
    semantic["revision"] = int(semantic.get("revision") or 0) + 1

    profile["semantic_understanding"] = semantic
    profile["story_summary"] = semantic.get("story_summary", "")
    profile["semantic_arc"] = semantic.get("emotional_arc", [])
    p.video_profile = json.dumps(profile, ensure_ascii=False)
    p.status = "profiled"
    db.commit()
    return profile


@router.post("/{project_id}/keypoints")
async def save_keypoints(
    project_id: str,
    body: KeyPointsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")

    p.key_points_json = json.dumps([kp.model_dump() for kp in body.keypoints], ensure_ascii=False)
    p.voice_regions_json = json.dumps([vr.model_dump() for vr in body.voice_regions], ensure_ascii=False)
    p.caption_events_json = json.dumps([ce.model_dump() for ce in body.caption_events], ensure_ascii=False)
    p.video_profile = None
    db.commit()
    return {"success": True, "count": len(body.keypoints)}


@router.delete("/{project_id}")
async def delete_project(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(VideoProject).filter(VideoProject.id == project_id, VideoProject.user_id == current_user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    for session in db.query(GenerationSession).filter(GenerationSession.project_id == project_id).all():
        if session.full_audio_path and os.path.exists(session.full_audio_path):
            os.remove(session.full_audio_path)
    for task in db.query(ExportTask).filter(ExportTask.project_id == project_id).all():
        if task.file_path and os.path.exists(task.file_path):
            os.remove(task.file_path)
    for post in db.query(CommunityPost).filter(CommunityPost.project_id == project_id).all():
        db.query(Comment).filter(Comment.post_id == post.id).delete()
        db.query(Like).filter(Like.post_id == post.id).delete()
        db.query(Collect).filter(Collect.post_id == post.id).delete()
        db.delete(post)
    db.query(GenerationTask).filter(GenerationTask.project_id == project_id).delete()
    db.query(GenerationSession).filter(GenerationSession.project_id == project_id).delete()
    db.query(ExportTask).filter(ExportTask.project_id == project_id).delete()
    db.query(MusicTimeline).filter(MusicTimeline.project_id == project_id).delete()
    if p.video_path and os.path.exists(p.video_path):
        os.remove(p.video_path)
    db.delete(p)
    db.commit()
    return {"detail": "已删除"}
