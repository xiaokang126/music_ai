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
ACE_MAX_REQUEST_SECONDS = float(os.getenv("ACE_MAX_REQUEST_SECONDS", "60"))
ACE_INFERENCE_STEPS = int(os.getenv("ACE_INFERENCE_STEPS", "12"))
ACE_MAX_MOVEMENTS = int(os.getenv("ACE_MAX_MOVEMENTS", "12"))


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


def _production_prompt_for_full_score(timeline_data: dict, target_duration: float | None = None) -> str:
    style = str(timeline_data.get("style") or "short video soundtrack").replace("_", " ")
    bpm = timeline_data.get("bpm", 90)
    key = str(timeline_data.get("key") or "C_major").replace("_", " ")
    global_caption = str(timeline_data.get("global_caption") or "").strip()
    segments = timeline_data.get("timeline", []) or []
    arc_parts = []
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        emotion = seg.get("emotion", "warm")
        energy = seg.get("energy", 0.5)
        instrument = seg.get("instrument", "main theme")
        arc_parts.append(f"{start}-{end}s {emotion} energy {energy} led by {instrument}")
    arc = "; ".join(arc_parts[:5])
    base = global_caption or (
        f"Create one continuous polished instrumental {style} score in {key}, around {bpm} BPM."
    )
    duration_text = f" The target video is {target_duration:.1f} seconds long;" if target_duration else ""
    return (
        f"{base}{duration_text} create a production-ready main cue that can sustain the full edit. "
        f"Full-video emotional arc: {arc}. "
        "Make it feel like one coherent soundtrack cue with a memorable main motif, natural intro, development and ending. "
        "Avoid a static drum loop: evolve the arrangement every 8-16 bars with tasteful changes in percussion, bass motion, harmony, melody, texture and density. "
        "The percussion must support the story instead of becoming the only distinctive element. "
        "Use loop-friendly phrasing only inside each movement, but preserve clear musical development across the full video. "
        "Keep internal timeline transitions continuous: no fade-out or fade-in at segment boundaries, no volume pumping between sections, consistent loudness across the full cue. "
        "Do not create a collage of stingers, risers, impacts or random sound effects. "
        "No vocals, no lyrics, dialogue-friendly mix, smooth dynamics, warm publish-ready short-video score."
    )


def _segments_for_window(timeline_data: dict, start: float, end: float) -> list[dict]:
    selected = []
    for seg in timeline_data.get("timeline", []) or []:
        try:
            seg_start = float(seg.get("start", 0) or 0)
            seg_end = float(seg.get("end", seg_start) or seg_start)
        except (TypeError, ValueError):
            continue
        if max(start, seg_start) < min(end, seg_end):
            selected.append(seg)
    return selected


def _movement_plan(target_duration: float) -> list[tuple[float, float]]:
    if target_duration <= ACE_MAX_REQUEST_SECONDS + 1:
        return [(0.0, target_duration)]
    target_chunk = max(25.0, min(ACE_MAX_REQUEST_SECONDS, 60.0))
    count = max(2, int((target_duration + target_chunk - 1) // target_chunk))
    count = min(max(2, ACE_MAX_MOVEMENTS), count)
    step = target_duration / count
    plan = []
    for idx in range(count):
        start = round(step * idx, 2)
        end = round(target_duration if idx == count - 1 else step * (idx + 1), 2)
        plan.append((start, end))
    return plan


def _segment_arc_text(segments: list[dict], limit: int = 6) -> str:
    parts = []
    for seg in segments[:limit]:
        parts.append(
            f"{seg.get('start', 0)}-{seg.get('end', 0)}s "
            f"{seg.get('emotion', 'warm')} energy {seg.get('energy', 0.5)} "
            f"led by {seg.get('instrument', 'main motif')}"
        )
    return "; ".join(parts)


def _production_prompt_for_movement(
    timeline_data: dict,
    *,
    movement_index: int,
    movement_total: int,
    start: float,
    end: float,
    target_duration: float,
) -> str:
    style = str(timeline_data.get("style") or "short video soundtrack").replace("_", " ")
    bpm = timeline_data.get("bpm", 90)
    key = str(timeline_data.get("key") or "C_major").replace("_", " ")
    global_caption = str(timeline_data.get("global_caption") or "").strip()
    semantic = timeline_data.get("semantic_understanding") if isinstance(timeline_data.get("semantic_understanding"), dict) else {}
    story = str(semantic.get("story_summary") or "").strip()
    director = str(semantic.get("music_director_brief") or "").strip()
    local_segments = _segments_for_window(timeline_data, start, end)
    local_arc = _segment_arc_text(local_segments) or "smooth emotional development with subtle dynamic motion"

    movement_role = "opening with a clear hook" if movement_index == 1 else (
        "final resolution with a natural ending" if movement_index == movement_total else "middle development with evolving layers"
    )
    continuity = "connect naturally from the previous movement" if movement_index > 1 else "establish the main motif"
    next_hint = "leave musical space for the next movement" if movement_index < movement_total else "finish with a resolved tail"

    return (
        f"{global_caption or f'Create a polished instrumental {style} score'} "
        f"This is movement {movement_index} of {movement_total}, covering video time {start:.1f}-{end:.1f}s "
        f"inside a {target_duration:.1f}s full video. Role: {movement_role}; {continuity}; {next_hint}. "
        f"Style {style}, key {key}, around {bpm} BPM. Local visual/emotional arc: {local_arc}. "
        f"Story context: {story or 'short-video emotional storytelling'}. Director intent: {director or 'match the video dynamics without overpowering original audio'}. "
        "Compose a real evolving background score, not a single distinctive drum loop. "
        "Vary drums, bass, harmony, motif, register, texture and density over time; add or remove layers every 8-16 bars while keeping the same musical identity. "
        "Percussion should be restrained and supportive, with melodic or harmonic material carrying the emotion. "
        "No hard fade-in or fade-out, no stingers, no random sound effects, no vocals, no lyrics, dialogue-friendly mix, stable loudness, publish-ready."
    )


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


def _fit_audio_to_duration(audio: AudioSegment, target_ms: int, fade_out_ms: int = 350) -> AudioSegment:
    target_ms = max(1000, int(target_ms))
    audio = audio.set_channels(2)
    if len(audio) == 0:
        return AudioSegment.silent(duration=target_ms).set_channels(2)
    if len(audio) >= target_ms:
        trimmed = audio[:target_ms]
        if fade_out_ms > 0:
            trimmed = trimmed.fade_out(min(fade_out_ms, target_ms // 4))
        return trimmed

    result = audio
    while len(result) < target_ms:
        crossfade = min(700, max(0, len(result) // 4), max(0, len(audio) // 4))
        if crossfade > 60:
            result = result.append(audio, crossfade=crossfade)
        else:
            result += audio
    result = result[:target_ms]
    if fade_out_ms > 0:
        result = result.fade_out(min(fade_out_ms, target_ms // 4))
    return result


def _normalize_ace_segment(input_path: str, output_path: str, target_seconds: float, fade_out_ms: int = 350) -> str:
    target_ms = max(1000, int(target_seconds * 1000))
    audio = AudioSegment.from_file(input_path).set_channels(2)
    fitted = _fit_audio_to_duration(audio, target_ms, fade_out_ms=fade_out_ms)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fitted.export(output_path, format="mp3", bitrate="320k")
    return output_path


def _concat_fitted_segments(segment_paths: list[str], output_path: str, target_ms: int, crossfade_ms: int = 0) -> str:
    combined = AudioSegment.silent(duration=0).set_channels(2)
    for path in segment_paths:
        chunk = AudioSegment.from_file(path).set_channels(2)
        if len(combined) and crossfade_ms > 0:
            combined = combined.append(chunk, crossfade=min(crossfade_ms, len(combined) // 4, len(chunk) // 4))
        else:
            combined += chunk
    combined = _fit_audio_to_duration(combined, target_ms, fade_out_ms=350)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined.export(output_path, format="mp3", bitrate="320k")
    return output_path


async def generate_bgm_for_timeline(timeline_data: dict, project_id: str) -> dict:
    """Generate one coherent full-video BGM with ACE-Step.

    The timeline remains useful for UI explanation and ducking, but BGM quality is
    better when ACE receives one full-score brief instead of several unrelated
    segment prompts that are later stitched together.
    """
    os.makedirs(settings.GENERATED_DIR, exist_ok=True)

    timeline = timeline_data.get("timeline", [])
    if not timeline:
        raise _ace_error("Music Timeline 中没有可生成的音乐段落")
    if not await ace_service_available():
        raise AceStepError(ace_unavailable_message())

    target_ms = _timeline_duration_ms(timeline_data)
    target_duration = max(1.0, target_ms / 1000)
    output_path = os.path.join(settings.GENERATED_DIR, f"{project_id}_bgm_full.mp3")
    plan = _movement_plan(target_duration)
    generated_paths: list[str] = []

    try:
        if len(plan) == 1:
            request_duration = min(target_duration, max(8.0, ACE_MAX_REQUEST_SECONDS))
            prompt = _production_prompt_for_full_score(timeline_data, target_duration=target_duration)
            task_id = await submit_ace_task(prompt, request_duration, inference_steps=ACE_INFERENCE_STEPS)
            result = await poll_ace_task(task_id, timeout=max(120.0, request_duration * 8))
            file_path = result.get("file", "")
            if not file_path:
                raise _ace_error(f"完整配乐生成结果没有 file 字段，响应：{json.dumps(result, ensure_ascii=False)[:500]}")
            raw_dest = os.path.join(settings.GENERATED_DIR, f"{project_id}_bgm_full_raw.mp3")
            await download_ace_audio(file_path, raw_dest)
            _normalize_ace_segment(raw_dest, output_path, target_duration)
        else:
            for idx, (start, end) in enumerate(plan, start=1):
                movement_duration = max(4.0, end - start)
                request_duration = min(movement_duration, max(8.0, ACE_MAX_REQUEST_SECONDS))
                prompt = _production_prompt_for_movement(
                    timeline_data,
                    movement_index=idx,
                    movement_total=len(plan),
                    start=start,
                    end=end,
                    target_duration=target_duration,
                )
                task_id = await submit_ace_task(prompt, request_duration, inference_steps=ACE_INFERENCE_STEPS)
                result = await poll_ace_task(task_id, timeout=max(120.0, request_duration * 8))
                file_path = result.get("file", "")
                if not file_path:
                    raise _ace_error(
                        f"第 {idx}/{len(plan)} 段配乐结果没有 file 字段，响应：{json.dumps(result, ensure_ascii=False)[:500]}"
                    )
                raw_dest = os.path.join(settings.GENERATED_DIR, f"{project_id}_movement_{idx:02d}_raw.mp3")
                fitted_dest = os.path.join(settings.GENERATED_DIR, f"{project_id}_movement_{idx:02d}.mp3")
                await download_ace_audio(file_path, raw_dest)
                _normalize_ace_segment(raw_dest, fitted_dest, movement_duration, fade_out_ms=0)
                generated_paths.append(fitted_dest)
            _concat_fitted_segments(generated_paths, output_path, target_ms, crossfade_ms=1400)
    except AceStepError as exc:
        raise _ace_error(f"完整配乐生成失败，{exc}") from exc
    except Exception as exc:
        raise _ace_error(f"处理完整配乐音频失败：{exc}") from exc

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise _ace_error("完整配乐生成后没有得到可用音频文件")

    final_ms = len(AudioSegment.from_file(output_path))
    if final_ms + 250 < target_ms:
        raise _ace_error(f"ACE 音频长度不足，目标 {target_ms / 1000:.2f}s，实际 {final_ms / 1000:.2f}s")
    logger.info(
        "ACE full-score generated project_id=%s movements=%s target_duration=%.2fs",
        project_id,
        len(plan),
        target_duration,
    )

    return {
        "success": True,
        "audio_path": output_path,
        "segment_count": len(timeline),
        "total_segments": len(timeline),
    }
