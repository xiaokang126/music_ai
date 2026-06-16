import json


def build_video_profile(
    project,
    scene_changes: list,
    key_points: list = None,
    voice_regions: list = None,
    caption_events: list = None,
) -> dict:
    """Build a complete video_profile.json from project data and auto-detected scene changes."""
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

    return {
        "video_id": project.id,
        "metadata": metadata,
        "video_type": project.video_type,
        "user_description": project.user_description or "",
        "scene_change_candidates": scene_changes,
        "key_events": key_points,
        "voice_regions": voice_regions,
        "caption_events": caption_events,
        "emotion_arc": emotion_arc,
    }
