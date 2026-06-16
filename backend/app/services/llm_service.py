import json
import re
import time
import httpx
from ..config import settings

SYSTEM_PROMPT = """你是短视频声音导演。请根据输入的视频信息生成严格的 JSON 格式配乐方案。

输出格式为 JSON，字段完整定义如下：
{
  "style": "风格模板，必须从 [healing_vlog, product_promo, hype_edit, campus_memory, emotional_story, knowledge_edu] 中选择",
  "bpm": "整数，40-200",
  "key": "调式，如 C_major, A_minor",
  "duration": "视频总秒数",
  "global_caption": "英语整体音乐制作描述",
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
1. 3-8个音乐段落，段间时间连续(start=上一段end)
2. importance=critical 的事件处必须有 sfx 或 beat_pattern
3. 转场点必须加 sfx
4. voice_regions 全部在 ducking_schedule 中覆盖
5. global_caption 和 caption 必须用英文，且要像给文生音乐模型的制作 brief：
   - caption 25-45 个英文单词，包含 genre, instrumentation, rhythm/tempo feel, emotion arc, mix style
   - 明确 no vocals, no lyrics，避免生成唱歌盖住视频人声
   - 有人声区间时描述为 understated / ducked / dialogue-friendly
   - 不要只写关键词，不要写中文，不要写解释
6. 段落之间要保持同一首歌的连贯感：同一调式、相近音色、逐段推进或回落
7. 普通用户作品优先选择清晰、现代、可发布的声音；不要生成实验噪音、刺耳高频或过满编曲

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

    if len(data["timeline"]) < 3 or len(data["timeline"]) > 8:
        raise ValueError("Timeline must contain 3-8 segments")

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
    return max(1.0, min(duration, 60.0))


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


STYLE_DEFAULTS = {
    "healing_vlog": (82, "C_major", ["calm", "warm", "calm"], ["soft_piano", "acoustic_guitar", "soft_piano"], [None, "simple_kick_snare", None]),
    "product_promo": (110, "G_major", ["excited", "energetic", "excited"], ["electronic_beat", "synth", "electronic"], ["energetic_beat", "energetic_beat", "trap_hats"]),
    "hype_edit": (135, "D_minor", ["intense", "excited", "intense"], ["electronic", "full_band", "electronic_beat"], ["energetic_beat", "trap_hats", "energetic_beat"]),
    "campus_memory": (90, "G_major", ["warm", "nostalgic", "warm"], ["acoustic_guitar", "piano_with_pad", "soft_piano"], [None, "lofi_beat", None]),
    "emotional_story": (72, "A_minor", ["sad", "nostalgic", "warm"], ["piano_with_strings", "orchestral", "soft_piano"], [None, None, None]),
    "knowledge_edu": (100, "C_major", ["calm", "warm", "calm"], ["lofi_beats", "synth", "pad"], ["lofi_beat", "lofi_beat", "lofi_beat"]),
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
    "hype_edit": "cinematic hype edit cue with dark synth pulses, punchy drums, risers, impacts, wide energetic mix",
    "campus_memory": "nostalgic campus memory soundtrack with acoustic guitar, soft piano, warm pad, light lofi groove, intimate mix",
    "emotional_story": "emotional short film underscore with felt piano, warm strings, subtle low pulse, restrained cinematic mix",
    "knowledge_edu": "friendly knowledge video bed with lofi drums, soft synth keys, light bass, clear dialogue-friendly mix",
}


def _caption_for_segment(style: str, bpm: int, key: str, emotion: str, instrument: str, energy: float, role: str) -> str:
    brief = STYLE_BRIEFS.get(style, STYLE_BRIEFS["campus_memory"])
    density = "minimal" if energy < 0.4 else "medium-density" if energy < 0.7 else "fuller"
    return (
        f"{brief}; {role} section in {key.replace('_', ' ')}, around {bpm} BPM, "
        f"{emotion} emotion led by {instrument}, {density} arrangement, smooth transitions, "
        "no vocals, no lyrics, dialogue-friendly, polished short-video soundtrack."
    )


def _default_timeline(style: str, duration: float, ducking_schedule: list[dict] | None = None) -> dict:
    """降级默认模板（LLM 不可用时使用）。"""
    bpm, key, emotions, instruments, beats = STYLE_DEFAULTS.get(style, STYLE_DEFAULTS["campus_memory"])
    s1 = round(duration / 3, 2)
    s2 = round(duration * 2 / 3, 2)
    starts = [0.0, s1, s2]
    ends = [s1, s2, round(duration, 2)]
    sfx_types = [None, {"type": "whoosh", "position": "start"}, {"type": "riser_reverse", "position": "end"}]
    segments = []
    progression = STYLE_PROGRESSIONS.get(style, STYLE_PROGRESSIONS["campus_memory"])
    roles = ["opening hook", "main emotional development", "resolution ending"]
    for i in range(3):
        segments.append({
            "segment_id": i + 1,
            "start": starts[i],
            "end": ends[i],
            "emotion": emotions[i],
            "energy": [0.35, 0.65, 0.3][i],
            "instrument": instruments[i],
            "progression": progression,
            "volume": [0.35, 0.52, 0.28][i],
            "sfx": sfx_types[i],
            "beat_pattern": beats[i],
            "fade": "fade_in" if i == 0 else "fade_out" if i == 2 else None,
            "caption": _caption_for_segment(
                style,
                bpm,
                key,
                emotions[i],
                instruments[i],
                [0.35, 0.65, 0.3][i],
                roles[i],
            ),
        })
    return {
        "style": style,
        "bpm": bpm,
        "key": key,
        "duration": round(duration, 2),
        "global_caption": (
            f"{STYLE_BRIEFS.get(style, STYLE_BRIEFS['campus_memory'])}; coherent {key.replace('_', ' ')} "
            f"arrangement at {bpm} BPM for emotional short-video storytelling, no vocals, no lyrics."
        ),
        "timeline": segments,
        "ducking_schedule": ducking_schedule or [],
    }


def generate_timeline(video_profile: dict, style: str) -> dict:
    """从 video_profile 生成 Music Timeline（调用智谱 GLM-4-Flash）。"""
    duration = _duration_from_profile(video_profile)
    fallback = _default_timeline(style, duration, _ducking_from_profile(video_profile))
    user_prompt = f"""请为以下视频生成 {style} 风格的配乐方案。

视频分析结果：
{json.dumps(video_profile, ensure_ascii=False, indent=2)}

创作要求：
- 面向普通用户发布作品，音乐要现代、耐听、情绪明确，像完整短视频配乐而不是素材片段。
- 优先保护视频原声和人声信息，voice_regions 内必须安排 ducking。
- caption 写成可直接给音乐生成模型使用的英文制作 brief，包含音色、节奏、情绪走向、混音要求，并写明 no vocals, no lyrics。
- 保持每个 segment 属于同一首歌，同一调式与相近主音色，转场自然。

只输出 JSON，不要解释。"""
    result = _call_provider(user_prompt, fallback)
    if not result.get("ducking_schedule"):
        result["ducking_schedule"] = fallback["ducking_schedule"]
    return result
