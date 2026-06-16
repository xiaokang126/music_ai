import os
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
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
from ..services.video_profile import build_video_profile

router = APIRouter(prefix="/api/video", tags=["video"])


@router.post("/upload", response_model=VideoProjectResponse)
async def upload(
    video: UploadFile = File(...),
    video_type: str = Form("campus_memory"),
    user_description: str = Form(""),
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
async def preview_video(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not p or not os.path.exists(p.video_path):
        raise HTTPException(status_code=404, detail="视频不存在")
    with open(p.video_path, "rb") as f:
        return Response(content=f.read(), media_type="video/mp4")


@router.get("/public/{project_id}/preview")
async def public_preview_video(project_id: str, db: Session = Depends(get_db)):
    """Public video preview - no auth required, for community embedding."""
    p = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not p or not os.path.exists(p.video_path):
        raise HTTPException(status_code=404, detail="视频不存在")
    with open(p.video_path, "rb") as f:
        return Response(content=f.read(), media_type="video/mp4")


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

    # Detect scenes and build profile
    scene_changes = detect_scene_changes(p.video_path)
    key_points = json.loads(p.key_points_json) if p.key_points_json else []
    voice_regions = json.loads(p.voice_regions_json) if p.voice_regions_json else []
    caption_events = json.loads(p.caption_events_json) if p.caption_events_json else []

    profile = build_video_profile(p, scene_changes, key_points, voice_regions, caption_events)
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
