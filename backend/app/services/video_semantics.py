import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from ..config import settings


QWEN_UTILS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Qwen2.5-VL", "qwen-vl-utils", "src")
)


@dataclass
class FrameFeature:
    time: float
    path: str
    brightness: float
    saturation: float
    contrast: float
    motion: float


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _duration(metadata: dict) -> float:
    return max(1.0, _float(metadata.get("duration"), 3.0))


def _frame_times(duration: float, scene_changes: list[dict] | None = None, max_frames: int | None = None) -> list[float]:
    max_frames = max(3, min(max_frames or settings.QWEN_VL_MAX_FRAMES, 8))
    if duration <= 4:
        base = [0.2, duration / 2, max(0.2, duration - 0.2)]
    else:
        base = [duration * i / (max_frames - 1) for i in range(max_frames)]
        base[0] = min(0.5, duration * 0.08)
        base[-1] = max(base[-1], duration - min(0.5, duration * 0.08))

    for point in scene_changes or []:
        t = _float(point.get("time"), -1)
        if 0.2 < t < duration - 0.2:
            base.append(t)

    deduped: list[float] = []
    for t in sorted(base):
        t = round(max(0, min(duration, t)), 2)
        if deduped and abs(t - deduped[-1]) < 0.35:
            continue
        deduped.append(t)
    if len(deduped) > max_frames:
        step = len(deduped) / max_frames
        deduped = [deduped[int(i * step)] for i in range(max_frames)]
    return deduped


def _safe_slug(project_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", project_id)


def extract_semantic_frames(
    video_path: str,
    project_id: str,
    metadata: dict,
    scene_changes: list[dict] | None = None,
    mode: str = "balanced",
) -> list[FrameFeature]:
    duration = _duration(metadata)
    max_frames = settings.QWEN_VL_MAX_FRAMES if mode == "balanced" else 4
    times = _frame_times(duration, scene_changes, max_frames=max_frames)
    out_dir = os.path.join(settings.GENERATED_DIR, "semantic_frames", _safe_slug(project_id))
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    previous_gray = None
    features: list[FrameFeature] = []
    try:
        for idx, t in enumerate(times):
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            height, width = frame.shape[:2]
            if width > 640:
                scale = 640 / width
                frame = cv2.resize(frame, (640, max(1, int(height * scale))))

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = float(np.mean(gray))
            saturation = float(np.mean(hsv[:, :, 1]))
            contrast = float(np.std(gray))
            motion = 0.0
            if previous_gray is not None:
                resized_prev = cv2.resize(previous_gray, (gray.shape[1], gray.shape[0]))
                motion = float(np.mean(cv2.absdiff(gray, resized_prev)))
            previous_gray = gray

            path = os.path.join(out_dir, f"frame_{idx:02d}_{t:.2f}.jpg")
            cv2.imwrite(path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 86])
            features.append(FrameFeature(t, path, brightness, saturation, contrast, motion))
    finally:
        cap.release()
    return features


def _visual_style(features: list[FrameFeature]) -> dict:
    if not features:
        return {"brightness": "unknown", "color": "unknown", "motion": "unknown", "contrast": "unknown"}
    brightness = float(np.mean([f.brightness for f in features]))
    saturation = float(np.mean([f.saturation for f in features]))
    contrast = float(np.mean([f.contrast for f in features]))
    motion = float(np.mean([f.motion for f in features[1:]] or [0]))
    return {
        "brightness": "bright" if brightness >= 165 else "dim" if brightness <= 85 else "normal",
        "color": "vivid" if saturation >= 85 else "muted" if saturation <= 42 else "natural",
        "motion": "active" if motion >= 24 else "steady" if motion <= 10 else "moderate",
        "contrast": "high" if contrast >= 62 else "soft" if contrast <= 34 else "balanced",
        "metrics": {
            "brightness": round(brightness, 2),
            "saturation": round(saturation, 2),
            "contrast": round(contrast, 2),
            "motion": round(motion, 2),
        },
    }


def _style_phrase(video_type: str) -> str:
    return {
        "healing_vlog": "日常疗愈影像",
        "product_promo": "产品或活动展示视频",
        "hype_edit": "节奏混剪视频",
        "campus_memory": "校园回忆视频",
        "emotional_story": "情感叙事视频",
        "knowledge_edu": "知识讲解视频",
    }.get(video_type, "短视频作品")


def _emotion_for(video_type: str, phase: float, motion: str) -> str:
    if video_type == "hype_edit":
        return "energetic" if motion in {"active", "moderate"} else "intense"
    if video_type == "emotional_story":
        return "nostalgic" if phase < 0.66 else "warm"
    if video_type == "campus_memory":
        return "warm" if phase < 0.4 else "nostalgic" if phase < 0.75 else "warm"
    if video_type == "product_promo":
        return "excited" if phase > 0.45 else "warm"
    if video_type == "knowledge_edu":
        return "calm" if phase < 0.5 else "warm"
    return "calm" if phase < 0.3 else "warm"


def _energy_for(motion: str, phase: float) -> float:
    base = 0.38 if motion == "steady" else 0.5 if motion == "moderate" else 0.62
    arc = 0.12 * (1 - abs(phase - 0.58) / 0.58)
    return round(max(0.25, min(0.82, base + arc)), 2)


def _fallback_understanding(
    *,
    project_id: str,
    metadata: dict,
    video_type: str,
    user_description: str,
    include_ocr: bool,
    frames: list[FrameFeature],
    qwen_reason: str,
) -> dict:
    duration = _duration(metadata)
    style = _visual_style(frames)
    label = _style_phrase(video_type)
    motion_cn = {"steady": "镜头节奏平稳", "moderate": "画面有一定运动", "active": "画面运动较强"}.get(style["motion"], "画面节奏未知")
    color_cn = {"vivid": "色彩鲜明", "muted": "色彩克制", "natural": "色彩自然"}.get(style["color"], "色彩未知")
    light_cn = {"bright": "整体较明亮", "dim": "整体偏暗", "normal": "亮度正常"}.get(style["brightness"], "亮度未知")
    user_part = f" 用户描述为：{user_description.strip()}" if user_description.strip() else ""
    summary = f"这是一段约 {duration:.1f} 秒的{label}，{light_cn}，{color_cn}，{motion_cn}。{user_part}".strip()

    if duration <= 4:
        boundaries = [0.0, round(duration / 3, 2), round(duration * 2 / 3, 2), round(duration, 2)]
    else:
        boundaries = [0.0, round(duration * 0.34, 2), round(duration * 0.68, 2), round(duration, 2)]

    arc = []
    for i in range(3):
        start, end = boundaries[i], boundaries[i + 1]
        phase = i / 2
        emotion = _emotion_for(video_type, phase, style["motion"])
        energy = _energy_for(style["motion"], phase)
        arc.append({
            "start": start,
            "end": end,
            "visual": f"{label}第 {i + 1} 段，{light_cn}，{color_cn}，{motion_cn}",
            "emotion": emotion,
            "energy": energy,
            "music_intent": (
                "保持连续主旋律，配乐不在段落边界淡出淡入；"
                "根据画面能量轻微推进，避免抢占原视频声音。"
            ),
        })

    return {
        "status": "fallback",
        "provider": "heuristic",
        "mode": "balanced",
        "qwen_status": {
            "available": False,
            "reason": qwen_reason,
        },
        "ocr_enabled": include_ocr,
        "ocr_status": "disabled" if not include_ocr else "not_available_without_qwen_or_ocr_engine",
        "story_summary": summary,
        "visual_style": style,
        "emotional_arc": arc,
        "caption_texts": [],
        "music_director_brief": (
            f"{summary} 配乐应是一首完整连续的背景音乐，围绕 {arc[0]['emotion']} 到 {arc[-1]['emotion']} 的情绪推进，"
            "不要生成随机音效堆叠，不要在内部段落反复淡入淡出，必要时在人声或重要画面处降低密度。"
        ),
        "frames": [{"time": f.time, "path": f.path} for f in frames],
        "warnings": ["当前未完成真实 Qwen2.5-VL 推理，已使用关键帧视觉统计与用户描述生成保底语义。"],
    }


def _extract_json(text: str) -> dict | None:
    text = (text or "").strip()
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _qwen_model_path() -> tuple[str, str]:
    model_path = settings.QWEN_VL_MODEL_PATH.strip()
    if not model_path:
        return "", "QWEN_VL_MODEL_PATH 未配置，未找到本地 Qwen2.5-VL 权重目录。"
    if os.path.exists(model_path):
        if not os.path.isdir(model_path):
            return "", f"QWEN_VL_MODEL_PATH={model_path} 不是模型权重目录。"
        config_path = os.path.join(model_path, "config.json")
        has_weights = any(
            name.endswith((".safetensors", ".bin", ".pt"))
            for name in os.listdir(model_path)
        )
        if not os.path.exists(config_path) or not has_weights:
            return "", (
                f"QWEN_VL_MODEL_PATH={model_path} 存在，但不是完整 Qwen2.5-VL checkpoint；"
                "需要 config.json 和模型权重文件。"
            )
        return model_path, ""
    if settings.QWEN_VL_ALLOW_REMOTE:
        return model_path, ""
    return "", f"QWEN_VL_MODEL_PATH={model_path} 不存在，且未开启 QWEN_VL_ALLOW_REMOTE。"


def _call_qwen(
    *,
    frames: list[FrameFeature],
    metadata: dict,
    video_type: str,
    user_description: str,
    include_ocr: bool,
) -> tuple[dict | None, str]:
    model_path, reason = _qwen_model_path()
    if not model_path:
        return None, reason
    if not frames:
        return None, "没有成功抽取关键帧，无法调用 Qwen。"

    try:
        if QWEN_UTILS_PATH not in sys.path:
            sys.path.insert(0, QWEN_UTILS_PATH)
        import torch
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
        from qwen_vl_utils import process_vision_info
    except Exception as exc:
        return None, f"Qwen 推理依赖不可用：{exc}"

    content = [
        {
            "type": "video",
            "video": [f"file://{frame.path}" for frame in frames],
            "resized_height": 280,
            "resized_width": 420,
        },
        {
            "type": "text",
            "text": (
                "你是短视频配乐导演。请理解这些按时间顺序抽取的视频关键帧，输出严格 JSON："
                "{story_summary, visual_style, emotional_arc, caption_texts, music_director_brief}。"
                "emotional_arc 每项包含 start,end,visual,emotion,energy,music_intent。"
                f"视频类型={video_type}，时长={_duration(metadata):.2f}s，用户描述={user_description or '无'}。"
                f"OCR={'需要识别画面文字' if include_ocr else '不需要识别字幕/OCR'}。"
                "不要解释，只输出 JSON。"
            ),
        },
    ]
    messages = [{"role": "user", "content": content}]

    try:
        processor = AutoProcessor.from_pretrained(model_path)
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_path,
            torch_dtype="auto",
            device_map=settings.QWEN_VL_DEVICE_MAP,
        )
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        images, videos, video_kwargs = process_vision_info(messages, return_video_kwargs=True)
        inputs = processor(text=[text], images=images, videos=videos, padding=True, return_tensors="pt", **video_kwargs)
        inputs = inputs.to(model.device)
        with torch.inference_mode():
            generated_ids = model.generate(**inputs, max_new_tokens=900)
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
    except Exception as exc:
        return None, f"Qwen 推理失败：{exc}"

    parsed = _extract_json(output_text)
    if not parsed:
        return None, f"Qwen 返回内容不是可解析 JSON：{output_text[:300]}"
    return parsed, ""


def _normalize_qwen_result(result: dict, fallback: dict, include_ocr: bool, frames: list[FrameFeature]) -> dict:
    story_summary = str(result.get("story_summary") or fallback["story_summary"]).strip()
    arc = result.get("emotional_arc") if isinstance(result.get("emotional_arc"), list) else fallback["emotional_arc"]
    normalized_arc = []
    duration = fallback["emotional_arc"][-1]["end"] if fallback.get("emotional_arc") else 1.0
    for idx, item in enumerate(arc[:8]):
        if not isinstance(item, dict):
            continue
        start = max(0.0, _float(item.get("start"), idx * duration / max(len(arc), 1)))
        end = max(start + 0.2, _float(item.get("end"), (idx + 1) * duration / max(len(arc), 1)))
        normalized_arc.append({
            "start": round(start, 2),
            "end": round(min(end, duration), 2),
            "visual": str(item.get("visual") or item.get("description") or fallback["emotional_arc"][min(idx, 2)]["visual"]),
            "emotion": str(item.get("emotion") or fallback["emotional_arc"][min(idx, 2)]["emotion"]),
            "energy": round(max(0.1, min(0.95, _float(item.get("energy"), fallback["emotional_arc"][min(idx, 2)]["energy"]))), 2),
            "music_intent": str(item.get("music_intent") or fallback["emotional_arc"][min(idx, 2)]["music_intent"]),
        })
    if len(normalized_arc) < 3:
        normalized_arc = fallback["emotional_arc"]

    return {
        "status": "completed",
        "provider": "qwen2.5-vl",
        "mode": "balanced",
        "qwen_status": {"available": True, "reason": ""},
        "ocr_enabled": include_ocr,
        "ocr_status": "completed" if include_ocr else "disabled",
        "story_summary": story_summary,
        "visual_style": result.get("visual_style") if isinstance(result.get("visual_style"), dict) else fallback["visual_style"],
        "emotional_arc": normalized_arc,
        "caption_texts": result.get("caption_texts") if isinstance(result.get("caption_texts"), list) else [],
        "music_director_brief": str(result.get("music_director_brief") or fallback["music_director_brief"]),
        "frames": [{"time": f.time, "path": f.path} for f in frames],
        "warnings": [],
    }


def analyze_video_semantics(
    *,
    video_path: str,
    project_id: str,
    metadata: dict,
    video_type: str,
    user_description: str = "",
    include_ocr: bool = False,
    scene_changes: list[dict] | None = None,
    mode: str = "balanced",
) -> dict:
    frames = extract_semantic_frames(video_path, project_id, metadata, scene_changes, mode=mode)
    fallback = _fallback_understanding(
        project_id=project_id,
        metadata=metadata,
        video_type=video_type,
        user_description=user_description,
        include_ocr=include_ocr,
        frames=frames,
        qwen_reason="Qwen 尚未调用",
    )
    qwen_result, reason = _call_qwen(
        frames=frames,
        metadata=metadata,
        video_type=video_type,
        user_description=user_description,
        include_ocr=include_ocr,
    )
    if qwen_result:
        return _normalize_qwen_result(qwen_result, fallback, include_ocr, frames)
    fallback["qwen_status"]["reason"] = reason
    return fallback
