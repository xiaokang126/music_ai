import subprocess
import json
import os
import asyncio
import tempfile
from typing import Optional
from PIL import Image
import numpy as np


async def extract_metadata(video_path: str) -> dict:
    """Extract video metadata with ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", video_path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            data = json.loads(stdout)
            video_stream = None
            for s in data.get("streams", []):
                if s.get("codec_type") == "video":
                    video_stream = s
                    break
            fmt = data.get("format", {})
            return {
                "duration": float(fmt.get("duration", 0)),
                "fps": _parse_fps(video_stream.get("r_frame_rate", "30/1")) if video_stream else 30,
                "resolution": {
                    "width": video_stream.get("width", 0) if video_stream else 0,
                    "height": video_stream.get("height", 0) if video_stream else 0,
                },
                "codec": video_stream.get("codec_name", "unknown") if video_stream else "unknown",
                "has_audio": any(s.get("codec_type") == "audio" for s in data.get("streams", [])),
            }
    except Exception:
        pass
    return {"duration": 0, "fps": 30, "resolution": {"width": 0, "height": 0}, "codec": "unknown", "has_audio": False}


def _parse_fps(r_frame_rate: str) -> float:
    try:
        parts = r_frame_rate.split("/")
        if len(parts) == 2 and int(parts[1]) != 0:
            return float(parts[0]) / float(parts[1])
    except (ValueError, ZeroDivisionError):
        pass
    return 30.0


def detect_scene_changes(video_path: str, interval: float = 0.5) -> list[dict]:
    """Detect scene changes by computing frame differences."""
    import tempfile

    temp_dir = tempfile.mkdtemp(prefix="musecut_frames_")
    try:
        # Extract frames at 2 fps
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vf", "fps=2",
             os.path.join(temp_dir, "frame_%04d.jpg")],
            capture_output=True,
            timeout=30,
        )

        frame_files = sorted([
            f for f in os.listdir(temp_dir) if f.endswith(".jpg")
        ])
        if len(frame_files) < 2:
            return []

        changes = []
        prev_img = None
        for i, fname in enumerate(frame_files):
            img = Image.open(os.path.join(temp_dir, fname)).convert("L").resize((160, 90))
            arr = np.array(img, dtype=np.float32)
            if prev_img is not None:
                diff = np.mean(np.abs(arr - prev_img))
                t = i * interval
                if diff > 30:
                    changes.append({"time": round(t, 1), "confidence": min(round(diff / 100, 2), 1.0), "type": "hard_cut"})
                elif diff > 15:
                    changes.append({"time": round(t, 1), "confidence": min(round(diff / 100, 2), 1.0), "type": "dissolve"})
            prev_img = arr

        return changes
    except Exception:
        return []
    finally:
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))
        os.rmdir(temp_dir)


def detect_rhythm_points(video_path: str, max_points: int = 180) -> list[dict]:
    """Detect musical/visual cut candidates from the original audio track.

    Uses librosa's battle-tested beat tracker and onset detector. The result is
    intentionally a compact set of timestamps so the timeline can snap segment
    boundaries and beat markers without overwhelming the UI.
    """
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = tmp.name

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "22050",
                "-f",
                "wav",
                tmp_path,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )

        try:
            return _detect_rhythm_points_librosa(tmp_path, max_points)
        except Exception:
            return _detect_rhythm_points_numpy(tmp_path, max_points)
    except Exception:
        return []
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def _dedupe_and_limit_points(points: list[dict], max_points: int) -> list[dict]:
    deduped: list[dict] = []
    for point in sorted(points, key=lambda p: (p["time"], -p["confidence"])):
        if deduped and abs(point["time"] - deduped[-1]["time"]) < 0.12:
            if point["confidence"] > deduped[-1]["confidence"]:
                deduped[-1] = point
            continue
        deduped.append(point)

    if len(deduped) > max_points:
        step = len(deduped) / max_points
        sampled = [deduped[int(i * step)] for i in range(max_points)]
        strongest = sorted(deduped, key=lambda p: p["confidence"], reverse=True)[: max_points // 4]
        merged = {(p["time"], p["type"]): p for p in sampled + strongest}
        deduped = sorted(merged.values(), key=lambda p: p["time"])[:max_points]
    return deduped


def _detect_rhythm_points_librosa(wav_path: str, max_points: int) -> list[dict]:
    import librosa

    y, sr = librosa.load(wav_path, sr=22050, mono=True)
    if y.size == 0:
        return []

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    onset_times = librosa.onset.onset_detect(
        y=y,
        sr=sr,
        units="time",
        backtrack=True,
        pre_max=3,
        post_max=3,
        pre_avg=6,
        post_avg=6,
        delta=0.18,
        wait=3,
    )

    env_max = float(np.max(onset_env)) if onset_env.size else 0.0

    def confidence_at(t: float, base: float) -> float:
        if env_max <= 0:
            return base
        frame = int(librosa.time_to_frames([t], sr=sr)[0])
        frame = max(0, min(frame, len(onset_env) - 1))
        return round(min(1.0, max(base, float(onset_env[frame]) / env_max)), 3)

    points: list[dict] = []
    for t in beat_times:
        if t >= 0.15:
            points.append({
                "time": round(float(t), 3),
                "confidence": confidence_at(float(t), 0.45),
                "type": "beat",
            })
    for t in onset_times:
        if t >= 0.15:
            points.append({
                "time": round(float(t), 3),
                "confidence": confidence_at(float(t), 0.55),
                "type": "onset",
            })

    points = _dedupe_and_limit_points(points, max_points)
    try:
        tempo_value = float(np.asarray(tempo).reshape(-1)[0])
    except Exception:
        tempo_value = 0.0
    for point in points:
        point["tempo"] = round(tempo_value, 2) if tempo_value else None
    return points


def _detect_rhythm_points_numpy(wav_path: str, max_points: int) -> list[dict]:
    from scipy.io import wavfile

    sr, data = wavfile.read(wav_path)
    if data.size == 0:
        return []
    if data.ndim > 1:
        data = data.mean(axis=1)
    y = data.astype(np.float32)
    peak = float(np.max(np.abs(y))) if y.size else 0.0
    if peak <= 0:
        return []
    y = y / peak

    frame = max(256, int(sr * 0.08))
    hop = max(128, int(sr * 0.02))
    rms = []
    for start in range(0, max(1, len(y) - frame), hop):
        chunk = y[start:start + frame]
        rms.append(float(np.sqrt(np.mean(chunk * chunk))))
    if len(rms) < 4:
        return []
    env = np.asarray(rms, dtype=np.float32)
    env = np.convolve(env, np.ones(3, dtype=np.float32) / 3, mode="same")
    novelty = np.maximum(0, np.diff(env, prepend=env[0]))
    threshold = float(np.mean(novelty) + np.std(novelty) * 1.1)
    max_novelty = float(np.max(novelty)) or 1.0
    min_distance = max(1, int(0.22 / (hop / sr)))

    points: list[dict] = []
    last_idx = -min_distance
    for idx in range(1, len(novelty) - 1):
        if idx - last_idx < min_distance:
            continue
        value = float(novelty[idx])
        if value < threshold:
            continue
        if value < float(novelty[idx - 1]) or value < float(novelty[idx + 1]):
            continue
        t = idx * hop / sr
        points.append({
            "time": round(float(t), 3),
            "confidence": round(min(1.0, max(0.45, value / max_novelty)), 3),
            "type": "onset",
            "tempo": None,
        })
        last_idx = idx

    return _dedupe_and_limit_points(points, max_points)
