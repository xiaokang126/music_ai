import subprocess
import json
import os
import asyncio
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
