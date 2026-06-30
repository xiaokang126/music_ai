import json


def build_video_profile(
    project,
    scene_changes: list,
    rhythm_points: list = None,
    key_points: list = None,
    voice_regions: list = None,
    caption_events: list = None,
    semantic_understanding: dict | None = None,
) -> dict:
    """Build a complete video_profile.json from project data and auto-detected scene changes."""
    if rhythm_points is None:
        rhythm_points = []
    if key_points is None:
        key_points = []
    if voice_regions is None:
        voice_regions = []
    if caption_events is None:
        caption_events = []

    metadata = json.loads(project.metadata_json) if project.metadata_json else {}

    # Build emotion arc from key events
    emotion_arc = []
    emotion_map = {
        "scene_start": ("calm", 0.3),
        "emotion_peak": ("happy", 0.9),
        "ending": ("calm", 0.2),
        "transition": ("warm", 0.5),
        "highlight": ("excited", 0.8),
        "scene_cut": ("intense", 0.7),
    }
    for ev in sorted(key_points, key=lambda e: e.get("time", 0)):
        mapped = emotion_map.get(ev.get("type", ""), ("warm", 0.5))
        emotion_arc.append({
            "time": ev.get("time", 0),
            "emotion": mapped[0],
            "intensity": mapped[1],
        })

    semantic_understanding = semantic_understanding or {}
    semantic_options = metadata.get("semantic_options") or {}

    return {
        "video_id": project.id,
        "metadata": metadata,
        "video_type": project.video_type,
        "user_description": project.user_description or "",
        "semantic_options": {
            "mode": semantic_options.get("mode") or semantic_understanding.get("mode") or "balanced",
            "ocr_enabled": bool(semantic_options.get("ocr_enabled", semantic_understanding.get("ocr_enabled", False))),
        },
        "semantic_understanding": semantic_understanding,
        "story_summary": semantic_understanding.get("story_summary", ""),
        "semantic_arc": semantic_understanding.get("emotional_arc", []),
        "scene_change_candidates": scene_changes,
        "rhythm_points": rhythm_points,
        "key_events": key_points,
        "voice_regions": voice_regions,
        "caption_events": caption_events,
        "emotion_arc": emotion_arc,
    }
