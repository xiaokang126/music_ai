import json
import logging
import os
import subprocess
import asyncio
import httpx
import time
from typing import Optional
from pydub import AudioSegment
from ..config import settings


class AceStepError(RuntimeError):
    """Raised when ACE-Step generation cannot complete."""


logger = logging.getLogger("musecut.acestep")


def _ace_error(message: str) -> AceStepError:
    return AceStepError(
        f"使用 ACE 调用失败：{message}。当前项目只允许使用 ACE 生成音频，未换用本地合成或其他降级策略。"
    )


def _network_error_detail(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: {exc}"


def _ace_http_timeout() -> httpx.Timeout:
    return httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)


def _is_transient_network_error(exc: Exception) -> bool:
    return isinstance(exc, (httpx.TransportError, OSError, BrokenPipeError))


def ace_unavailable_message() -> str:
    return str(_ace_error(f"ACE-Step 服务不可用或无法连接，地址：{settings.ACESTEP_API_URL}"))


async def ace_service_available() -> bool:
    """Fast availability probe for ACE-Step.

    A 404 still means a server is reachable; connection failures mean we should
    use the local demo synthesizer in auto mock mode.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
            resp = await client.get(f"{settings.ACESTEP_API_URL}/health")
            return resp.status_code < 500
    except Exception:
        return False


async def submit_ace_task(prompt: str, duration: float = 3.0, inference_steps: int = 8) -> Optional[str]:
    """Submit a music generation task to ACE-Step REST API."""
    payload = {
        "prompt": prompt,
        "lyrics": "[Instrumental]",
        "thinking": False,
        "inference_steps": inference_steps,
        "audio_duration": duration,
        "duration": duration,
        "audio_format": "mp3",
    }
    max_attempts = 2
    last_network_error = ""
    try:
        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=_ace_http_timeout(), trust_env=False) as client:
                    resp = await client.post(
                        f"{settings.ACESTEP_API_URL}/release_task",
                        json=payload,
                    )
                break
            except Exception as exc:
                if not _is_transient_network_error(exc):
                    raise
                last_network_error = _network_error_detail(exc)
                logger.warning(
                    "ACE release_task transient network error attempt=%s/%s api_url=%s duration=%.2f error=%s",
                    attempt,
                    max_attempts,
                    settings.ACESTEP_API_URL,
                    duration,
                    last_network_error,
                )
                if attempt >= max_attempts:
                    raise _ace_error(
                        f"提交生成任务异常：{last_network_error}；已重试 {max_attempts} 次，ACE 地址：{settings.ACESTEP_API_URL}"
                    ) from exc
                await asyncio.sleep(1.0 * attempt)
        else:
            raise _ace_error(f"提交生成任务异常：{last_network_error or '未知网络错误'}")

        if resp is None:
            raise _ace_error(f"提交生成任务异常：{last_network_error or '没有收到 ACE 响应'}")

        try:
            if resp.status_code != 200:
                raise _ace_error(f"提交生成任务失败，HTTP {resp.status_code}，响应：{resp.text[:500]}")
            data = resp.json()
            inner = data.get("data", {})
            task_id = inner.get("task_id")
            if not task_id:
                raise _ace_error(f"提交生成任务后没有返回 task_id，响应：{json.dumps(data, ensure_ascii=False)[:500]}")
            return task_id
        except AceStepError:
            raise
        except Exception as exc:
            raise _ace_error(f"解析提交任务响应异常：{_network_error_detail(exc)}") from exc
    except AceStepError:
        raise
    except Exception as exc:
        raise _ace_error(f"提交生成任务异常：{_network_error_detail(exc)}") from exc


async def poll_ace_task(task_id: str, timeout: float = 120.0) -> Optional[dict]:
    """Poll ACE-Step task until completion. Returns result dict with 'file' key."""
    start = time.time()
    last_error = ""
    async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
        while time.time() - start < timeout:
            try:
                resp = await client.post(
                    f"{settings.ACESTEP_API_URL}/query_result",
                    json={"task_id_list": [task_id]},
                )
                if resp.status_code != 200:
                    last_error = f"HTTP {resp.status_code}，响应：{resp.text[:500]}"
                    await asyncio.sleep(2)
                    continue
                data = resp.json()
                results = data.get("data", [])
                if results:
                    r = results[0]
                    if r.get("status") == 1:  # success
                        result_str = r.get("result", "[]")
                        try:
                            parsed = json.loads(result_str)
                            if isinstance(parsed, list) and len(parsed) > 0:
                                return parsed[0]
                        except json.JSONDecodeError as exc:
                            raise _ace_error(f"解析任务结果失败，task_id={task_id}，原始结果：{result_str[:500]}") from exc
                        return {"file": "", "status": "ok_raw"}
                    if r.get("status") == 2:  # failed
                        raise _ace_error(f"ACE 任务执行失败，task_id={task_id}，响应：{json.dumps(r, ensure_ascii=False)[:500]}")
            except AceStepError:
                raise
            except Exception as exc:
                last_error = str(exc)
            await asyncio.sleep(2)
    detail = f"，最后一次错误：{last_error}" if last_error else ""
    raise _ace_error(f"轮询 ACE 任务超时，task_id={task_id}{detail}")


async def download_ace_audio(file_url: str, dest_path: str) -> bool:
    """Download generated audio from ACE-Step server.
    file_url is the path returned by ACE-Step, e.g. '/v1/audio?path=%2Fhome%2F...'
    which is relative to ACESTEP_API_URL."""
    try:
        # The file_url from ACE-Step result is already a full relative URL path
        url = f"{settings.ACESTEP_API_URL}{file_url}"
        max_attempts = 2
        last_network_error = ""
        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=_ace_http_timeout(), trust_env=False) as client:
                    resp = await client.get(url)
                break
            except Exception as exc:
                if not _is_transient_network_error(exc):
                    raise
                last_network_error = _network_error_detail(exc)
                logger.warning(
                    "ACE audio download transient network error attempt=%s/%s url=%s error=%s",
                    attempt,
                    max_attempts,
                    url,
                    last_network_error,
                )
                if attempt >= max_attempts:
                    raise _ace_error(
                        f"下载生成音频异常：{last_network_error}；已重试 {max_attempts} 次，URL={url}"
                    ) from exc
                await asyncio.sleep(1.0 * attempt)
        else:
            raise _ace_error(f"下载生成音频异常：{last_network_error or '未知网络错误'}，URL={url}")

        if resp is None:
            raise _ace_error(f"下载生成音频异常：{last_network_error or '没有收到 ACE 响应'}，URL={url}")

        try:
            if resp.status_code == 200:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                return True
            raise _ace_error(f"下载生成音频失败，HTTP {resp.status_code}，URL={url}，响应：{resp.text[:500]}")
        except AceStepError:
            raise
        except Exception as exc:
            raise _ace_error(f"保存生成音频异常：{_network_error_detail(exc)}，URL={url}") from exc
    except AceStepError:
        raise
    except Exception as exc:
        raise _ace_error(f"下载生成音频异常：{_network_error_detail(exc)}") from exc


def _production_prompt_for_segment(timeline_data: dict, seg: dict) -> str:
    caption = str(seg.get("caption") or seg.get("prompt") or "soft cinematic background music").strip()
    lowered = caption.lower()
    constraints = []
    if "no vocals" not in lowered:
        constraints.append("no vocals")
    if "no lyrics" not in lowered:
        constraints.append("no lyrics")
    if "dialogue" not in lowered:
        constraints.append("dialogue-friendly mix")

    style = str(timeline_data.get("style") or "short video soundtrack").replace("_", " ")
    bpm = timeline_data.get("bpm", 90)
    key = str(timeline_data.get("key") or "C_major").replace("_", " ")
    emotion = seg.get("emotion", "warm")
    instrument = seg.get("instrument", "modern acoustic and synth palette")
    energy = seg.get("energy", 0.5)
    extra = ", ".join(constraints)
    suffix = (
        f" Create a polished instrumental {style} cue in {key}, around {bpm} BPM, "
        f"{emotion} emotional arc, led by {instrument}, energy {energy}. "
        "Keep it coherent with adjacent timeline segments, clean low end, smooth transitions, publish-ready short-video score."
    )
    if extra:
        suffix += f" Required: {extra}."
    return f"{caption}. {suffix}"


def _timeline_duration_ms(timeline_data: dict) -> int:
    duration = 0.0
    try:
        duration = float(timeline_data.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    for seg in timeline_data.get("timeline", []) or []:
        try:
            duration = max(duration, float(seg.get("end", 0) or 0))
        except (TypeError, ValueError):
            continue
    return max(1000, int(duration * 1000))


def _segment_duration_seconds(seg: dict) -> float:
    try:
        start = float(seg.get("start", 0) or 0)
        end = float(seg.get("end", start) or start)
    except (TypeError, ValueError):
        return 1.0
    return max(1.0, end - start)


def _fit_audio_to_duration(audio: AudioSegment, target_ms: int) -> AudioSegment:
    target_ms = max(1000, int(target_ms))
    audio = audio.set_channels(2)
    if len(audio) == 0:
        return AudioSegment.silent(duration=target_ms).set_channels(2)
    if len(audio) >= target_ms:
        return audio[:target_ms].fade_out(min(350, target_ms // 4))

    result = audio
    while len(result) < target_ms:
        crossfade = min(700, max(0, len(result) // 4), max(0, len(audio) // 4))
        if crossfade > 60:
            result = result.append(audio, crossfade=crossfade)
        else:
            result += audio
    return result[:target_ms].fade_out(min(350, target_ms // 4))


def _normalize_ace_segment(input_path: str, output_path: str, target_seconds: float) -> str:
    target_ms = max(1000, int(target_seconds * 1000))
    audio = AudioSegment.from_file(input_path).set_channels(2)
    fitted = _fit_audio_to_duration(audio, target_ms)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fitted.export(output_path, format="mp3", bitrate="320k")
    return output_path


def _concat_fitted_segments(segment_paths: list[str], output_path: str, target_ms: int) -> str:
    combined = AudioSegment.silent(duration=0).set_channels(2)
    for path in segment_paths:
        combined += AudioSegment.from_file(path).set_channels(2)
    combined = _fit_audio_to_duration(combined, target_ms)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined.export(output_path, format="mp3", bitrate="320k")
    return output_path


async def generate_bgm_for_timeline(timeline_data: dict, project_id: str) -> dict:
    """Generate BGM for each timeline segment using ACE-Step and concatenate."""
    os.makedirs(settings.GENERATED_DIR, exist_ok=True)

    timeline = timeline_data.get("timeline", [])
    if not timeline:
        raise _ace_error("Music Timeline 中没有可生成的音乐段落")
    if not await ace_service_available():
        raise AceStepError(ace_unavailable_message())

    segments_audio = []
    for i, seg in enumerate(timeline):
        caption = _production_prompt_for_segment(timeline_data, seg)
        duration = _segment_duration_seconds(seg)

        try:
            task_id = await submit_ace_task(caption, duration)
            result = await poll_ace_task(task_id)
        except AceStepError as exc:
            raise _ace_error(f"第 {i + 1} 段生成失败，{exc}") from exc

        file_path = result.get("file", "")
        if not file_path:
            raise _ace_error(f"第 {i + 1} 段生成结果没有 file 字段，响应：{json.dumps(result, ensure_ascii=False)[:500]}")

        raw_dest = os.path.join(settings.GENERATED_DIR, f"{project_id}_seg_{i}_raw.mp3")
        fitted_dest = os.path.join(settings.GENERATED_DIR, f"{project_id}_seg_{i}.mp3")
        await download_ace_audio(file_path, raw_dest)
        _normalize_ace_segment(raw_dest, fitted_dest, duration)
        segments_audio.append(fitted_dest)
        logger.info("ACE segment generated project_id=%s segment=%s duration=%.2fs", project_id, i, duration)

    output_path = os.path.join(settings.GENERATED_DIR, f"{project_id}_bgm_full.mp3")
    try:
        _concat_fitted_segments(segments_audio, output_path, _timeline_duration_ms(timeline_data))
    except Exception as exc:
        raise _ace_error(f"拼接 ACE 音频片段失败：{exc}") from exc

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise _ace_error("拼接完成后没有得到可用音频文件")

    final_ms = len(AudioSegment.from_file(output_path))
    target_ms = _timeline_duration_ms(timeline_data)
    if final_ms + 250 < target_ms:
        raise _ace_error(f"ACE 音频长度不足，目标 {target_ms / 1000:.2f}s，实际 {final_ms / 1000:.2f}s")

    return {
        "success": True,
        "audio_path": output_path,
        "segment_count": len(segments_audio),
        "total_segments": len(timeline),
    }
