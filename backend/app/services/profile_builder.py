import json

from ..models.video_model import VideoProject
from .video_analyzer import detect_scene_changes, detect_rhythm_points
from .video_profile import build_video_profile
from .video_semantics import analyze_video_semantics


def loads_json(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def metadata_for_project(project: VideoProject) -> dict:
    metadata = loads_json(project.metadata_json, {})
    if not isinstance(metadata, dict):
        metadata = {}
    semantic_options = metadata.setdefault("semantic_options", {})
    semantic_options.setdefault("mode", "balanced")
    semantic_options.setdefault("ocr_enabled", False)
    return metadata


def build_profile_for_project(project: VideoProject) -> dict:
    metadata = metadata_for_project(project)
    semantic_options = metadata.get("semantic_options") or {}
    scene_changes = detect_scene_changes(project.video_path)
    rhythm_points = detect_rhythm_points(project.video_path)
    key_points = loads_json(project.key_points_json, [])
    voice_regions = loads_json(project.voice_regions_json, [])
    caption_events = loads_json(project.caption_events_json, [])
    semantic_understanding = analyze_video_semantics(
        video_path=project.video_path,
        project_id=project.id,
        metadata=metadata,
        video_type=project.video_type,
        user_description=project.user_description or "",
        include_ocr=bool(semantic_options.get("ocr_enabled", False)),
        scene_changes=scene_changes,
        mode="balanced",
    )
    return build_video_profile(
        project,
        scene_changes,
        rhythm_points,
        key_points,
        voice_regions,
        caption_events,
        semantic_understanding,
    )
