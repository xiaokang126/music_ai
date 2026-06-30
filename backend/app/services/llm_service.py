import json
import re
import time
import httpx
from ..config import settings

SYSTEM_PROMPT = """你是短视频配乐导演。请根据输入的视频信息生成严格的 JSON 格式配乐方案。

核心目标：输出要像“一位配乐导演为视频设计了一首完整、连贯、可发布的背景配乐”，而不是把音效、鼓点和转场素材堆在视频上。

输出格式为 JSON，字段完整定义如下：
{
  "style": "风格模板，必须从 [healing_vlog, product_promo, hype_edit, campus_memory, emotional_story, knowledge_edu] 中选择",
  "bpm": "整数，40-200",
  "key": "调式，如 C_major, A_minor",
  "duration": "视频总秒数",
  "global_caption": "英语整体音乐制作描述",
  "beat_points": [{"time": "秒数", "confidence": "0-1", "type": "beat/onset"}],
  "cut_points": [{"time": "秒数", "confidence": "0-1", "type": "scene/beat/onset/key_event"}],
  "timeline": [
    {
      "segment_id": "从1递增", "start": "秒数", "end": "秒数",
      "emotion": "从 [calm, warm, happy, intense, sad, excited, nostalgic, mysterious, energetic] 选择",
      "energy": "0.0-1.0", "instrument": "乐器英文名",
      "progression": ["和弦"], "volume": "0.0-1.0",
      "sfx": null 或 {"type":"whoosh/hit/impact/riser","position":"start/middle/end"},
      "beat_pattern": null 或 "simple_kick_snare/energetic_beat/lofi_beat/trap_hats",
      "fade": null 或 "fade_in/fade_out/fade_out_start",
      "caption": "英文音乐生成描述"
    }
  ],
  "ducking_schedule": [{"start":s,"end":e,"reduce_db":6-10}]
}

强制规则：
1. 3-12个音乐段落，段间时间连续(start=上一段end)，段落只用于描述同一首配乐的情绪推进；长视频必须增加段落密度，覆盖完整视频时长
2. 默认不要添加 sfx；只有非常明确的视觉转折、产品冲击或卡点剪辑才允许添加 1 个以内 sfx
3. 默认不要额外添加 beat_pattern；除 product_promo/hype_edit 外，beat_pattern 应优先为 null。即使需要节奏，也应让 ACE 生成在 BGM 内部，而不是依赖外部鼓点叠加
4. voice_regions 全部在 ducking_schedule 中覆盖
5. global_caption 和 caption 必须用英文，且要像给文生音乐模型的制作 brief：
   - caption 25-45 个英文单词，包含 genre, instrumentation, rhythm/tempo feel, emotion arc, mix style
   - 明确 no vocals, no lyrics，避免生成唱歌盖住视频人声
   - 有人声区间时描述为 understated / ducked / dialogue-friendly
   - 不要只写关键词，不要写中文，不要写解释
6. 段落之间要保持同一首歌的连贯感：同一调式、相近主音色、自然推进或回落，不要每段换一种声音
7. 普通用户作品优先选择清晰、现代、可发布的声音；不要生成实验噪音、刺耳高频或过满编曲
8. global_caption 是最重要字段，必须描述完整视频级配乐：genre、main instrumentation、emotional arc、tempo feel、dialogue-friendly mix、no vocals/no lyrics
9. 如果输入包含 rhythm_points 或 scene_change_candidates，内部段落边界必须优先贴近这些时间点；beat_points/cut_points 可以直接复用输入的关键卡点候选

风格参考：
- healing_vlog: bpm 70-90, 钢琴/吉他/pad
- product_promo: bpm 100-120, 电子/强鼓点
- hype_edit: bpm 120-150, 强鼓点/电子
- campus_memory: bpm 80-100, 吉他/钢琴
- emotional_story: bpm 60-85, 钢琴/弦乐
- knowledge_edu: bpm 90-110, lofi/合成器

只输出JSON，不要解释。"""


def _strip_json_content(content: str) -> dict:
    content = re.sub(r"^```(?:json)?\s*", "", content.strip())
    content = re.sub(r"\s*```$", "", content.strip())
    return json.loads(content)


def _call_zhipu(prompt: str, fallback: dict) -> dict:
    """调用智谱 GLM-4-Flash API 生成 Timeline JSON。"""
    if not settings.GLM_API_KEY:
        return fallback

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.GLM_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.GLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    for attempt in range(3):
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]

                result = _strip_json_content(content)
                _validate_timeline(result, fallback["duration"])
                return result
        except (json.JSONDecodeError, KeyError, ValueError, httpx.HTTPError):
            if attempt == 2:
                return fallback
            time.sleep(1)

    return fallback


def _call_openai_compatible(prompt: str, fallback: dict) -> dict:
    """Call a local OpenAI-compatible server, e.g. vLLM/llama.cpp server."""
    if not settings.LLM_BASE_URL:
        return fallback

    url = settings.LLM_BASE_URL.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/v1/chat/completions"

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }
    for attempt in range(3):
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                result = _strip_json_content(content)
                _validate_timeline(result, fallback["duration"])
                return result
        except (json.JSONDecodeError, KeyError, ValueError, httpx.HTTPError):
            if attempt == 2:
                return fallback
            time.sleep(1)
    return fallback


def _call_ollama(prompt: str, fallback: dict) -> dict:
    """Call local Ollama chat API."""
    base_url = settings.LLM_BASE_URL or "http://localhost:11434"
    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3},
    }
    for attempt in range(3):
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                content = resp.json()["message"]["content"]
                result = _strip_json_content(content)
                _validate_timeline(result, fallback["duration"])
                return result
        except (json.JSONDecodeError, KeyError, ValueError, httpx.HTTPError):
            if attempt == 2:
                return fallback
            time.sleep(1)
    return fallback


def _call_provider(prompt: str, fallback: dict) -> dict:
    provider = (settings.LLM_PROVIDER or "glm").lower()
    if provider == "ollama":
        return _call_ollama(prompt, fallback)
    if provider in {"openai_compatible", "vllm", "local"}:
        return _call_openai_compatible(prompt, fallback)
    return _call_zhipu(prompt, fallback)


def _validate_timeline(data: dict, expected_duration: float | None = None):
    """校验 timeline JSON 结构。"""
    if "timeline" not in data or not isinstance(data["timeline"], list):
        raise ValueError("Missing timeline array")

    if len(data["timeline"]) < 3 or len(data["timeline"]) > 12:
        raise ValueError("Timeline must contain 3-12 segments")

    if expected_duration:
        data["duration"] = expected_duration

    prev_end = 0.0
    for i, seg in enumerate(data["timeline"]):
        start = float(seg.get("start", prev_end))
        end = float(seg.get("end", start))
        if i == 0:
            start = 0.0
        elif abs(start - prev_end) > 0.05:
            start = prev_end
        if expected_duration and i == len(data["timeline"]) - 1:
            end = expected_duration
        if start >= end:
            raise ValueError(f"Segment {i}: start >= end")
        seg["start"] = round(start, 2)
        seg["end"] = round(end, 2)
        seg["volume"] = max(0, min(1.0, seg.get("volume", 0.5)))
        seg["energy"] = max(0, min(1.0, seg.get("energy", 0.5)))
        seg["segment_id"] = i + 1
        prev_end = end


def _duration_from_profile(video_profile: dict) -> float:
    metadata = video_profile.get("metadata", {}) if isinstance(video_profile, dict) else {}
    try:
        duration = float(metadata.get("duration") or video_profile.get("duration") or 15.0)
    except (TypeError, ValueError):
        duration = 15.0
    return max(1.0, min(duration, 900.0))


def _ducking_from_profile(video_profile: dict) -> list[dict]:
    schedule = []
    for region in video_profile.get("voice_regions", []) or []:
        start = region.get("start", region.get("start_time", 0))
        end = region.get("end", region.get("end_time", 0))
        try:
            start_f, end_f = float(start), float(end)
        except (TypeError, ValueError):
            continue
        if end_f > start_f:
            schedule.append({"start": round(start_f, 2), "end": round(end_f, 2), "reduce_db": 8})
    return schedule


def _point_time(point: dict) -> float | None:
    try:
        return float(point.get("time", point.get("start", 0)) or 0)
    except (TypeError, ValueError):
        return None


def _cut_candidates_from_profile(video_profile: dict, duration: float) -> list[dict]:
    candidates: list[dict] = []

    for point in video_profile.get("scene_change_candidates", []) or []:
        t = _point_time(point)
        if t is None:
            continue
        candidates.append({
            "time": round(t, 3),
            "confidence": max(0.55, min(1.0, float(point.get("confidence", 0.6) or 0.6))),
            "type": point.get("type") or "scene",
        })

    for point in video_profile.get("rhythm_points", []) or []:
        t = _point_time(point)
        if t is None:
            continue
        kind = point.get("type") or "beat"
        base = 0.48 if kind == "beat" else 0.58
        candidates.append({
            "time": round(t, 3),
            "confidence": max(base, min(1.0, float(point.get("confidence", base) or base))),
            "type": kind,
        })

    for point in video_profile.get("key_events", []) or []:
        t = _point_time(point)
        if t is None:
            continue
        candidates.append({
            "time": round(t, 3),
            "confidence": 0.92 if point.get("importance") in {"critical", "high"} else 0.75,
            "type": point.get("type") or "key_event",
        })

    filtered = [
        p for p in candidates
        if 0.25 < p["time"] < max(0.5, duration - 0.25)
    ]
    deduped: list[dict] = []
    for point in sorted(filtered, key=lambda p: (p["time"], -p["confidence"])):
        if deduped and abs(point["time"] - deduped[-1]["time"]) < 0.25:
            if point["confidence"] > deduped[-1]["confidence"]:
                deduped[-1] = point
            continue
        deduped.append(point)
    return deduped


def _beat_points_from_profile(video_profile: dict, duration: float, limit: int = 240) -> list[dict]:
    points = []
    for point in video_profile.get("rhythm_points", []) or []:
        t = _point_time(point)
        if t is None or t < 0 or t > duration:
            continue
        points.append({
            "time": round(t, 3),
            "confidence": max(0.0, min(1.0, float(point.get("confidence", 0.5) or 0.5))),
            "type": point.get("type") or "beat",
        })
    if len(points) <= limit:
        return points
    step = len(points) / limit
    sampled = [points[int(i * step)] for i in range(limit)]
    strongest = sorted(points, key=lambda p: p["confidence"], reverse=True)[: limit // 4]
    merged = {(p["time"], p["type"]): p for p in sampled + strongest}
    return sorted(merged.values(), key=lambda p: p["time"])[:limit]


def _target_segment_count(duration: float) -> int:
    if duration <= 18:
        return 3
    if duration <= 45:
        return 4
    if duration <= 90:
        return 5
    if duration <= 180:
        return 7
    if duration <= 360:
        return 9
    return 12


def _choose_boundaries(duration: float, candidates: list[dict], count: int) -> list[float]:
    if count <= 1:
        return [0.0, round(duration, 2)]

    boundaries = [0.0]
    min_gap = max(0.75, min(12.0, duration / max(count * 2.4, 1)))
    window = max(1.0, min(18.0, duration / max(count * 2.8, 1)))
    used: set[int] = set()

    for i in range(1, count):
        ideal = duration * i / count
        best_idx = None
        best_score = -999.0
        for idx, point in enumerate(candidates):
            if idx in used:
                continue
            t = point["time"]
            if t <= boundaries[-1] + min_gap or t >= duration - min_gap:
                continue
            distance = abs(t - ideal)
            if distance > window:
                continue
            score = float(point.get("confidence", 0.5)) * 2 - distance / max(window, 0.1)
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_idx is not None:
            used.add(best_idx)
            boundary = candidates[best_idx]["time"]
        else:
            boundary = ideal
        boundary = max(boundaries[-1] + min_gap, min(boundary, duration - min_gap))
        boundaries.append(round(boundary, 2))

    boundaries.append(round(duration, 2))
    return boundaries


STYLE_DEFAULTS = {
    "healing_vlog": (82, "C_major", ["calm", "warm", "calm"], ["felt_piano", "nylon_guitar_and_pad", "felt_piano"], [None, None, None]),
    "product_promo": (108, "G_major", ["warm", "excited", "happy"], ["rounded_synth_bass", "bright_plucks", "clean_synth_layers"], [None, "simple_kick_snare", None]),
    "hype_edit": (128, "D_minor", ["mysterious", "intense", "energetic"], ["dark_synth_pulse", "cinematic_drums", "wide_synth_bass"], [None, "energetic_beat", None]),
    "campus_memory": (88, "G_major", ["warm", "nostalgic", "warm"], ["acoustic_guitar", "soft_piano_and_pad", "felt_piano"], [None, None, None]),
    "emotional_story": (72, "A_minor", ["sad", "nostalgic", "warm"], ["felt_piano", "warm_strings", "soft_piano"], [None, None, None]),
    "knowledge_edu": (94, "C_major", ["calm", "warm", "calm"], ["soft_synth_keys", "lofi_texture", "warm_pad"], [None, None, None]),
}


STYLE_PROGRESSIONS = {
    "healing_vlog": ["C", "G", "Am", "F"],
    "product_promo": ["G", "D", "Em", "C"],
    "hype_edit": ["Dm", "Bb", "F", "C"],
    "campus_memory": ["G", "D", "Em", "C"],
    "emotional_story": ["Am", "F", "C", "G"],
    "knowledge_edu": ["C", "Em", "F", "G"],
}


STYLE_BRIEFS = {
    "healing_vlog": "modern healing vlog score with felt piano, nylon guitar, soft warm pad, gentle pulse, spacious natural mix",
    "product_promo": "clean product promo music with rounded synth bass, bright plucks, tight electronic drums, polished commercial mix",
    "hype_edit": "cinematic hype edit score with dark synth pulses, controlled drums, gradual build, wide energetic mix",
    "campus_memory": "nostalgic campus memory soundtrack with acoustic guitar, soft piano, warm pad, light lofi groove, intimate mix",
    "emotional_story": "emotional short film underscore with felt piano, warm strings, subtle low pulse, restrained cinematic mix",
    "knowledge_edu": "friendly knowledge video bed with lofi drums, soft synth keys, light bass, clear dialogue-friendly mix",
}


ALLOWED_EMOTIONS = {
    "calm", "warm", "happy", "intense", "sad", "excited", "nostalgic", "mysterious", "energetic"
}


def _semantic_understanding(video_profile: dict) -> dict:
    semantic = video_profile.get("semantic_understanding") if isinstance(video_profile, dict) else {}
    return semantic if isinstance(semantic, dict) else {}


def _semantic_arc(video_profile: dict) -> list[dict]:
    semantic = _semantic_understanding(video_profile)
    arc = semantic.get("emotional_arc") or video_profile.get("semantic_arc") or []
    return [item for item in arc if isinstance(item, dict)]


def _semantic_for_window(arc: list[dict], start: float, end: float) -> dict | None:
    if not arc:
        return None
    best = None
    best_overlap = 0.0
    midpoint = (start + end) / 2
    for item in arc:
        try:
            item_start = float(item.get("start", 0) or 0)
            item_end = float(item.get("end", item_start) or item_start)
        except (TypeError, ValueError):
            continue
        overlap = max(0.0, min(end, item_end) - max(start, item_start))
        if item_start <= midpoint <= item_end:
            overlap += 0.001
        if overlap > best_overlap:
            best = item
            best_overlap = overlap
    return best


def _semantic_emotion(value: str | None, fallback: str) -> str:
    emotion = (value or "").strip().lower()
    return emotion if emotion in ALLOWED_EMOTIONS else fallback


def _semantic_energy(value, fallback: float) -> float:
    try:
        energy = float(value)
    except (TypeError, ValueError):
        return fallback
    return round(max(0.18, min(0.9, fallback * 0.35 + energy * 0.65)), 2)


def _instrument_for_emotion(style: str, emotion: str, fallback: str) -> str:
    if style in {"product_promo", "hype_edit"}:
        return fallback
    return {
        "calm": "felt_piano_and_warm_pad",
        "warm": "acoustic_guitar_and_soft_piano",
        "happy": "bright_piano_and_light_plucks",
        "intense": "low_strings_and_soft_pulse",
        "sad": "felt_piano_and_warm_strings",
        "excited": "rhythmic_plucks_and_light_percussion",
        "nostalgic": "soft_piano_acoustic_guitar_and_pad",
        "mysterious": "muted_piano_and_dark_pad",
        "energetic": "clean_synth_plucks_and_subtle_drums",
    }.get(emotion, fallback)


def _semantic_brief(video_profile: dict) -> str:
    semantic = _semantic_understanding(video_profile)
    story = (semantic.get("story_summary") or video_profile.get("story_summary") or "").strip()
    director = (semantic.get("music_director_brief") or "").strip()
    if story and director:
        return f"Story context: {story} Director brief: {director}"
    if story:
        return f"Story context: {story}"
    if director:
        return f"Director brief: {director}"
    return "Story context: short-video emotional storytelling with clear visual pacing."


def _caption_for_segment(
    style: str,
    bpm: int,
    key: str,
    emotion: str,
    instrument: str,
    energy: float,
    role: str,
    semantic_item: dict | None = None,
) -> str:
    brief = STYLE_BRIEFS.get(style, STYLE_BRIEFS["campus_memory"])
    density = "minimal" if energy < 0.4 else "medium-density" if energy < 0.7 else "fuller"
    semantic_note = ""
    if semantic_item:
        visual = str(semantic_item.get("visual") or "")[:120]
        intent = str(semantic_item.get("music_intent") or "")[:120]
        if visual or intent:
            semantic_note = f" Match the visual story: {visual}. Follow this director intent: {intent}."
    return (
        f"{brief}; {role} section in {key.replace('_', ' ')}, around {bpm} BPM, "
        f"{emotion} emotion led by {instrument}, {density} arrangement, smooth transitions, "
        "no vocals, no lyrics, dialogue-friendly, no sound effects, coherent polished short-video score."
        f"{semantic_note}"
    )


def _default_timeline(
    style: str,
    duration: float,
    ducking_schedule: list[dict] | None = None,
    video_profile: dict | None = None,
) -> dict:
    """降级默认模板（LLM 不可用时使用）。"""
    bpm, key, emotions, instruments, beats = STYLE_DEFAULTS.get(style, STYLE_DEFAULTS["campus_memory"])
    video_profile = video_profile or {}
    candidates = _cut_candidates_from_profile(video_profile, duration)
    segment_count = _target_segment_count(duration)
    boundaries = _choose_boundaries(duration, candidates, segment_count)
    segments = []
    progression = STYLE_PROGRESSIONS.get(style, STYLE_PROGRESSIONS["campus_memory"])
    roles = [
        "opening hook",
        "early development",
        "main emotional development",
        "momentum lift",
        "turning point",
        "second development",
        "emotional peak",
        "release",
        "closing preparation",
        "final lift",
        "resolution",
        "ending tail",
    ]
    semantic_arc = _semantic_arc(video_profile)
    for i in range(segment_count):
        phase = i / max(1, segment_count - 1)
        energy = round(0.34 + (0.34 * (1 - abs(phase - 0.58) / 0.58)), 2)
        if i == 0 or i == segment_count - 1:
            energy = min(energy, 0.38)
        emotion = emotions[min(i, len(emotions) - 1)] if segment_count <= 3 else emotions[min(round(phase * (len(emotions) - 1)), len(emotions) - 1)]
        instrument = instruments[min(round(phase * (len(instruments) - 1)), len(instruments) - 1)]
        beat = beats[min(round(phase * (len(beats) - 1)), len(beats) - 1)]
        semantic_item = _semantic_for_window(semantic_arc, boundaries[i], boundaries[i + 1])
        if semantic_item:
            emotion = _semantic_emotion(semantic_item.get("emotion"), emotion)
            energy = _semantic_energy(semantic_item.get("energy"), energy)
            instrument = _instrument_for_emotion(style, emotion, instrument)
        segments.append({
            "segment_id": i + 1,
            "start": boundaries[i],
            "end": boundaries[i + 1],
            "emotion": emotion,
            "energy": energy,
            "instrument": instrument,
            "progression": progression,
            "volume": round(0.32 + energy * 0.32, 2),
            "sfx": None,
            "beat_pattern": beat if style in {"product_promo", "hype_edit"} and energy > 0.55 else None,
            "fade": "fade_in" if i == 0 else "fade_out" if i == segment_count - 1 else None,
            "caption": _caption_for_segment(
                style,
                bpm,
                key,
                emotion,
                instrument,
                energy,
                roles[min(i, len(roles) - 1)],
                semantic_item,
            ),
        })
    beat_points = _beat_points_from_profile(video_profile, duration)
    semantic_brief = _semantic_brief(video_profile)
    return {
        "style": style,
        "bpm": bpm,
        "key": key,
        "duration": round(duration, 2),
        "global_caption": (
            f"{STYLE_BRIEFS.get(style, STYLE_BRIEFS['campus_memory'])}; coherent {key.replace('_', ' ')} "
            f"arrangement at {bpm} BPM for emotional short-video storytelling. {semantic_brief} "
            "Make one continuous full-length instrumental cue "
            "with a clear opening, gentle development and natural ending, no vocals, no lyrics, no external sound effects, dialogue-friendly mix."
        ),
        "beat_points": beat_points,
        "cut_points": candidates[:160],
        "timeline": segments,
        "ducking_schedule": ducking_schedule or [],
    }


def _snap_segments_to_candidates(data: dict, video_profile: dict, duration: float) -> dict:
    timeline = data.get("timeline", []) or []
    if len(timeline) < 3:
        return data
    candidates = _cut_candidates_from_profile(video_profile, duration)
    if not candidates:
        return data

    count = len(timeline)
    boundaries = _choose_boundaries(duration, candidates, count)
    for i, seg in enumerate(timeline):
        seg["start"] = boundaries[i]
        seg["end"] = boundaries[i + 1]
        seg["segment_id"] = i + 1
    data["timeline"] = timeline
    data["duration"] = round(duration, 2)
    return data


def _postprocess_timeline(data: dict, style: str, video_profile: dict, fallback: dict) -> dict:
    duration = fallback["duration"]
    target_count = _target_segment_count(duration)
    timeline = data.get("timeline", []) or []

    # Long videos need enough editable musical sections. Some LLMs still return
    # only 3 generic segments, so expand with deterministic beat-aware sections.
    if duration > 90 and len(timeline) < max(6, target_count - 2):
        expanded = _default_timeline(style, duration, fallback.get("ducking_schedule", []), video_profile)
        if data.get("global_caption"):
            expanded["global_caption"] = data["global_caption"]
        data = expanded
    else:
        data = _snap_segments_to_candidates(data, video_profile, duration)

    data["duration"] = round(duration, 2)
    data["beat_points"] = _beat_points_from_profile(video_profile, duration)
    data["cut_points"] = _cut_candidates_from_profile(video_profile, duration)[:160]
    data["semantic_understanding"] = _semantic_understanding(video_profile)
    if not data.get("ducking_schedule"):
        data["ducking_schedule"] = fallback.get("ducking_schedule", [])
    _validate_timeline(data, duration)
    return data


def generate_timeline(video_profile: dict, style: str) -> dict:
    """从 video_profile 生成 Music Timeline（调用智谱 GLM-4-Flash）。"""
    duration = _duration_from_profile(video_profile)
    fallback = _default_timeline(style, duration, _ducking_from_profile(video_profile), video_profile)
    semantic = _semantic_understanding(video_profile)
    semantic_payload = {
        "story_summary": semantic.get("story_summary") or video_profile.get("story_summary") or "",
        "visual_style": semantic.get("visual_style") or {},
        "emotional_arc": semantic.get("emotional_arc") or video_profile.get("semantic_arc") or [],
        "caption_texts": semantic.get("caption_texts") or [],
        "music_director_brief": semantic.get("music_director_brief") or "",
        "ocr_enabled": semantic.get("ocr_enabled", False),
        "provider": semantic.get("provider", ""),
    }
    user_prompt = f"""请为以下视频生成 {style} 风格的配乐方案。

视频语义理解摘要（优先参考，它描述画面内容、情绪走向和配乐导演意图）：
{json.dumps(semantic_payload, ensure_ascii=False, indent=2)}

视频分析结果：
{json.dumps(video_profile, ensure_ascii=False, indent=2)}

创作要求：
- 面向普通用户发布作品，音乐要现代、耐听、情绪明确，像完整短视频配乐而不是素材片段。
- 必须覆盖完整视频时长 {duration:.2f} 秒，最后一个 segment.end 必须等于视频总时长。
- 长视频需要更多可编辑段落；不要把几分钟视频压成 3 个巨大段落。
- 这是“配乐主线”生成，不是效果器编排；不要为了展示功能而堆叠 Beat 或 SFX。
- 优先保护视频原声和人声信息，voice_regions 内必须安排 ducking。
- 如果有 rhythm_points / scene_change_candidates，段落边界、beat_points 和 cut_points 优先贴近这些时间点，形成更准的卡点。
- caption 写成可直接给音乐生成模型使用的英文制作 brief，包含音色、节奏、情绪走向、混音要求，并写明 no vocals, no lyrics。
- 保持每个 segment 属于同一首歌，同一调式与相近主音色，转场自然。
- global_caption 要能直接生成整条视频的完整 BGM；segment caption 只描述这首 BGM 的局部情绪变化。

只输出 JSON，不要解释。"""
    result = _call_provider(user_prompt, fallback)
    return _postprocess_timeline(result, style, video_profile, fallback)
