import os
import re
import subprocess
import tempfile
from typing import Optional

from pydub import AudioSegment
from pydub.generators import Sine, WhiteNoise


NOTE_OFFSETS = {
    "C": 0,
    "C#": 1,
    "D": 2,
    "D#": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "G": 7,
    "G#": 8,
    "A": 9,
    "A#": 10,
    "B": 11,
}

STYLE_PROGRESSIONS = {
    "healing_vlog": ["C", "G", "Am", "F"],
    "product_promo": ["G", "D", "Em", "C"],
    "hype_edit": ["Dm", "Bb", "F", "C"],
    "campus_memory": ["G", "D", "Em", "C"],
    "emotional_story": ["Am", "F", "C", "G"],
    "knowledge_edu": ["C", "Em", "F", "G"],
}

EMOTION_MOTIFS = {
    "calm": [0, 2, 4, 2],
    "warm": [0, 2, 4, 5],
    "happy": [0, 2, 4, 7],
    "intense": [0, 4, 5, 7],
    "sad": [0, 2, 1, 0],
    "excited": [0, 4, 7, 5],
    "nostalgic": [4, 2, 0, 2],
    "mysterious": [0, 1, 4, 3],
    "energetic": [0, 4, 5, 7],
}


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _float_value(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int_bpm(timeline_data: dict) -> int:
    return int(_clamp(_float_value(timeline_data.get("bpm"), 90), 40, 200))


def _key_parts(key: str) -> tuple[str, str]:
    key = str(key or "C_major")
    root = key.split("_")[0] if "_" in key else key
    mode = "minor" if "minor" in key.lower() else "major"
    return root or "C", mode


def _note_offset(note: str) -> int:
    note = str(note or "C").strip()
    if not note:
        return 0
    root = note[0].upper()
    accidental = note[1:2]
    offset = NOTE_OFFSETS.get(root, 0)
    if accidental == "#":
        offset += 1
    elif accidental == "b":
        offset -= 1
    return offset % 12


def _note_frequency(note: str, octave: int = 4) -> float:
    semitone = _note_offset(note) + (octave - 4) * 12
    return 261.63 * (2 ** (semitone / 12))


def _chord_frequencies(chord: str, octave: int = 4) -> list[float]:
    match = re.match(r"^\s*([A-Ga-g])([#b]?)(.*)$", str(chord or "C").strip())
    if not match:
        return [_note_frequency("C", octave), _note_frequency("E", octave), _note_frequency("G", octave)]

    root = f"{match.group(1).upper()}{match.group(2)}"
    suffix = match.group(3).lower()
    if "sus2" in suffix:
        intervals = [0, 2, 7]
    elif "sus" in suffix:
        intervals = [0, 5, 7]
    elif "dim" in suffix:
        intervals = [0, 3, 6]
    elif suffix.startswith("m") and not suffix.startswith("maj"):
        intervals = [0, 3, 7]
    else:
        intervals = [0, 4, 7]

    if "maj7" in suffix:
        intervals.append(11)
    elif "7" in suffix:
        intervals.append(10)

    root_freq = _note_frequency(root, octave)
    return [root_freq * (2 ** (interval / 12)) for interval in dict.fromkeys(intervals)]


def _progression_for_segment(timeline_data: dict, seg: dict) -> list[str]:
    raw = seg.get("progression")
    if isinstance(raw, list):
        progression = [str(chord).strip() for chord in raw if str(chord).strip()]
        if progression:
            return progression
    style = str(timeline_data.get("style") or "campus_memory")
    return STYLE_PROGRESSIONS.get(style, STYLE_PROGRESSIONS["campus_memory"])


def _scale_frequency(root: str, mode: str, degree: int, octave: int = 5) -> float:
    scale = [0, 2, 3, 5, 7, 8, 10] if mode == "minor" else [0, 2, 4, 5, 7, 9, 11]
    degree = int(degree)
    octave_shift = degree // len(scale)
    semitone = scale[degree % len(scale)] + octave_shift * 12
    return _note_frequency(root, octave) * (2 ** (semitone / 12))


def _safe_tone(freq: float, duration: int, gain: float) -> AudioSegment:
    duration = max(30, int(duration))
    return Sine(max(20, float(freq))).to_audio_segment(duration=duration).apply_gain(gain)


def _master_music(audio: AudioSegment, target_peak: float = -3.0) -> AudioSegment:
    audio = audio.set_channels(2)
    if len(audio) == 0 or audio.max_dBFS == float("-inf"):
        return audio
    audio = audio.high_pass_filter(35).low_pass_filter(14500)
    gain = target_peak - audio.max_dBFS
    if gain > 0:
        gain = min(gain, 5.0)
    audio = audio.apply_gain(gain)
    if audio.max_dBFS > target_peak:
        audio = audio.apply_gain(target_peak - audio.max_dBFS)
    return audio


def _loop_to_duration(audio: AudioSegment, target_ms: int) -> AudioSegment:
    if len(audio) >= target_ms:
        return audio[:target_ms]
    result = audio
    while len(result) < target_ms:
        crossfade = min(500, max(0, len(result) // 4), max(0, len(audio) // 4))
        if crossfade > 40:
            result = result.append(audio, crossfade=crossfade)
        else:
            result += audio
    return result[:target_ms]


def _duration_ms(timeline_data: dict, bgm: Optional[AudioSegment] = None) -> int:
    duration = float(timeline_data.get("duration") or 0)
    for seg in timeline_data.get("timeline", []) or []:
        duration = max(duration, float(seg.get("end", 0) or 0))
    if bgm is not None:
        duration = max(duration, bgm.duration_seconds)
    return max(1000, int(duration * 1000))


def _load_bgm(path: Optional[str], timeline_data: dict) -> AudioSegment:
    if path and os.path.exists(path):
        bgm = _master_music(AudioSegment.from_file(path).set_channels(2), target_peak=-4.0)
    else:
        bgm = _synth_bgm(timeline_data)

    target_ms = _duration_ms(timeline_data, bgm)
    if len(bgm) < target_ms:
        bgm = _loop_to_duration(bgm, target_ms)
    return bgm[:target_ms].fade_out(min(900, target_ms // 5))


def _segment_gain(seg: dict, base: float = -31.0) -> float:
    energy = _clamp(_float_value(seg.get("energy"), 0.45), 0, 1)
    volume = _clamp(_float_value(seg.get("volume"), 0.45), 0, 1)
    return base + energy * 7 + volume * 6


def _render_chord_layer(timeline_data: dict, seg: dict, duration: int) -> AudioSegment:
    layer = AudioSegment.silent(duration=duration).set_channels(2)
    bpm = _int_bpm(timeline_data)
    bar_ms = max(900, int(240000 / bpm))
    chord_ms = max(900, min(bar_ms * 2, duration))
    progression = _progression_for_segment(timeline_data, seg)
    energy = _clamp(_float_value(seg.get("energy"), 0.45), 0, 1)
    gain = _segment_gain(seg)

    position = 0
    chord_index = 0
    while position < duration:
        length = min(chord_ms, duration - position)
        freqs = _chord_frequencies(progression[chord_index % len(progression)], octave=4)
        chord_audio = AudioSegment.silent(duration=length).set_channels(2)
        for note_index, freq in enumerate(freqs[:4]):
            note_gain = gain - note_index * 2.8
            tone = _safe_tone(freq, length, note_gain).low_pass_filter(3200)
            chord_audio = chord_audio.overlay(tone)
        root_pad = _safe_tone(freqs[0] / 2, length, gain - 10).low_pass_filter(650)
        upper_air = _safe_tone(freqs[-1] * 2, length, gain - 17 + energy * 2).high_pass_filter(900)
        chord_audio = chord_audio.overlay(root_pad).overlay(upper_air)
        fade = min(450, max(80, length // 4))
        layer = layer.overlay(chord_audio.fade_in(fade).fade_out(fade), position=position)
        position += length
        chord_index += 1
    return layer


def _render_bass_layer(timeline_data: dict, seg: dict, duration: int) -> AudioSegment:
    layer = AudioSegment.silent(duration=duration).set_channels(2)
    energy = _clamp(_float_value(seg.get("energy"), 0.45), 0, 1)
    if energy < 0.22:
        return layer

    bpm = _int_bpm(timeline_data)
    beat_ms = max(300, int(60000 / bpm))
    step = beat_ms if energy > 0.62 or seg.get("beat_pattern") else beat_ms * 2
    pulse_ms = max(120, int(beat_ms * (0.62 if energy > 0.6 else 0.78)))
    progression = _progression_for_segment(timeline_data, seg)
    chord_ms = max(900, int(240000 / bpm))
    gain = -28 + energy * 5

    position = 0
    while position < duration:
        chord = progression[(position // chord_ms) % len(progression)]
        root = _chord_frequencies(chord, octave=2)[0]
        pulse = _safe_tone(root, min(pulse_ms, duration - position), gain).low_pass_filter(420)
        pulse = pulse.fade_out(min(160, len(pulse) // 2))
        layer = layer.overlay(pulse, position=position)
        position += step
    return layer


def _render_motif_layer(timeline_data: dict, seg: dict, duration: int) -> AudioSegment:
    layer = AudioSegment.silent(duration=duration).set_channels(2)
    energy = _clamp(_float_value(seg.get("energy"), 0.45), 0, 1)
    if energy < 0.28:
        return layer

    root, mode = _key_parts(str(timeline_data.get("key") or "C_major"))
    bpm = _int_bpm(timeline_data)
    beat_ms = max(300, int(60000 / bpm))
    note_ms = max(180, int(beat_ms * (0.52 if energy > 0.62 else 0.8)))
    bar_ms = beat_ms * 4
    emotion = str(seg.get("emotion") or "warm")
    motif = EMOTION_MOTIFS.get(emotion, EMOTION_MOTIFS["warm"])
    gain = _segment_gain(seg, base=-35.0)
    phrase_gap = bar_ms if energy > 0.58 else bar_ms * 2

    phrase_start = beat_ms
    while phrase_start < duration:
        position = phrase_start
        for degree in motif:
            if position >= duration:
                break
            freq = _scale_frequency(root, mode, degree, octave=5)
            note = _safe_tone(freq, min(note_ms, duration - position), gain)
            note = note.overlay(_safe_tone(freq * 2, len(note), gain - 13)).low_pass_filter(5200)
            note = note.fade_in(min(18, len(note) // 4)).fade_out(min(110, len(note) // 2))
            layer = layer.overlay(note, position=position)
            position += beat_ms if energy < 0.62 else beat_ms // 2
        phrase_start += phrase_gap
    return layer


def _render_texture_layer(seg: dict, duration: int) -> AudioSegment:
    energy = _clamp(_float_value(seg.get("energy"), 0.45), 0, 1)
    texture = WhiteNoise().to_audio_segment(duration=duration)
    texture = texture.high_pass_filter(6500).low_pass_filter(12000).apply_gain(-48 + energy * 3)
    return texture.fade_in(min(500, duration // 4)).fade_out(min(650, duration // 3)).set_channels(2)


def _render_segment_music(timeline_data: dict, seg: dict, duration: int, is_first: bool, is_last: bool) -> AudioSegment:
    segment = AudioSegment.silent(duration=duration).set_channels(2)
    segment = segment.overlay(_render_chord_layer(timeline_data, seg, duration))
    segment = segment.overlay(_render_bass_layer(timeline_data, seg, duration))
    segment = segment.overlay(_render_motif_layer(timeline_data, seg, duration))
    segment = segment.overlay(_render_texture_layer(seg, duration))

    fade_in = 650 if is_first or seg.get("fade") == "fade_in" else 250
    fade_out = 850 if is_last or seg.get("fade") in {"fade_out", "fade_out_start"} else 320
    return segment.fade_in(min(fade_in, duration // 3)).fade_out(min(fade_out, duration // 3))


def _synth_bgm(timeline_data: dict) -> AudioSegment:
    target_ms = _duration_ms(timeline_data)
    base = AudioSegment.silent(duration=target_ms).set_channels(2)
    timeline = timeline_data.get("timeline", []) or []
    if not timeline:
        timeline = [{"start": 0, "end": target_ms / 1000, "emotion": "warm", "energy": 0.35, "volume": 0.4}]

    for i, seg in enumerate(timeline):
        start = int(float(seg.get("start", 0)) * 1000)
        end = int(float(seg.get("end", 0)) * 1000)
        dur = max(120, end - start)
        segment = _render_segment_music(
            timeline_data,
            seg,
            dur,
            is_first=i == 0,
            is_last=i == len(timeline) - 1,
        )
        base = base.overlay(segment, position=start)
    return _master_music(base.fade_in(min(450, target_ms // 5)).fade_out(min(900, target_ms // 4)), target_peak=-4.0)


def _apply_ducking(bgm: AudioSegment, timeline_data: dict) -> AudioSegment:
    result = bgm
    for d in timeline_data.get("ducking_schedule", []) or []:
        start = max(0, int(float(d.get("start", 0)) * 1000))
        end = min(len(result), int(float(d.get("end", 0)) * 1000))
        reduce_db = abs(float(d.get("reduce_db", 8) or 8))
        if end <= start:
            continue
        result = result[:start] + (result[start:end] - reduce_db) + result[end:]
    return result


def _kick() -> AudioSegment:
    return Sine(55).to_audio_segment(duration=120).apply_gain(-6).fade_out(90).set_channels(2)


def _snare() -> AudioSegment:
    return WhiteNoise().to_audio_segment(duration=90).high_pass_filter(1200).apply_gain(-16).fade_out(70).set_channels(2)


def _hat() -> AudioSegment:
    return WhiteNoise().to_audio_segment(duration=35).high_pass_filter(5000).apply_gain(-24).fade_out(25).set_channels(2)


def _render_beat_track(timeline_data: dict, target_ms: int) -> AudioSegment:
    beat = AudioSegment.silent(duration=target_ms).set_channels(2)
    bpm = max(40, min(200, int(timeline_data.get("bpm", 90) or 90)))
    beat_ms = int(60000 / bpm)

    for seg in timeline_data.get("timeline", []) or []:
        pattern = seg.get("beat_pattern")
        if not pattern:
            continue
        start = int(float(seg.get("start", 0)) * 1000)
        end = int(float(seg.get("end", 0)) * 1000)
        step = beat_ms // 2 if pattern in {"trap_hats", "energetic_beat"} else beat_ms
        t = start
        count = 0
        while t < end:
            if count % 4 == 0:
                beat = beat.overlay(_kick(), position=t)
            if count % 4 == 2:
                beat = beat.overlay(_snare(), position=t)
            if pattern in {"lofi_beat", "trap_hats", "energetic_beat"}:
                beat = beat.overlay(_hat(), position=t)
            t += max(60, step)
            count += 1
    return beat


def _sfx_audio(kind: str, custom_sfx_paths: Optional[dict[str, str]] = None) -> AudioSegment:
    if custom_sfx_paths and kind in custom_sfx_paths and os.path.exists(custom_sfx_paths[kind]):
        return AudioSegment.from_file(custom_sfx_paths[kind]).set_channels(2).apply_gain(-2)
    if kind == "impact":
        return _kick().apply_gain(3).overlay(Sine(90).to_audio_segment(duration=320).apply_gain(-10).fade_out(260)).set_channels(2)
    if kind == "hit":
        return _snare().apply_gain(2)
    if kind == "riser":
        return Sine(220).to_audio_segment(duration=900).fade_in(700).apply_gain(-16).set_channels(2)
    if kind == "riser_reverse":
        return Sine(220).to_audio_segment(duration=900).fade_out(700).apply_gain(-16).set_channels(2)
    # whoosh/default
    return WhiteNoise().to_audio_segment(duration=450).high_pass_filter(1800).fade_in(40).fade_out(380).apply_gain(-20).set_channels(2)


def _render_sfx_track(timeline_data: dict, target_ms: int, custom_sfx_paths: Optional[dict[str, str]] = None) -> AudioSegment:
    sfx_track = AudioSegment.silent(duration=target_ms).set_channels(2)
    for seg in timeline_data.get("timeline", []) or []:
        node = seg.get("sfx")
        if not node:
            continue
        start = float(seg.get("start", 0) or 0)
        end = float(seg.get("end", start) or start)
        pos = node.get("position", "start")
        if pos == "middle":
            at = (start + end) / 2
        elif pos == "end":
            at = end
        else:
            at = start
        audio = _sfx_audio(node.get("type", "whoosh"), custom_sfx_paths)
        sfx_track = sfx_track.overlay(audio, position=max(0, int(at * 1000)))
    return sfx_track


def render_mixed_audio(
    timeline_data: dict,
    bgm_path: Optional[str],
    output_path: str,
    fmt: str,
    custom_sfx_paths: Optional[dict[str, str]] = None,
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bgm = _apply_ducking(_load_bgm(bgm_path, timeline_data), timeline_data)
    target_ms = _duration_ms(timeline_data, bgm)
    beat = _render_beat_track(timeline_data, target_ms)
    sfx = _render_sfx_track(timeline_data, target_ms, custom_sfx_paths)
    mixed = _master_music(bgm.overlay(beat).overlay(sfx), target_peak=-1.2)

    export_format = "mp3" if fmt == "mp3" else fmt
    kwargs = {"bitrate": "320k"} if fmt == "mp3" else {}
    mixed.export(output_path, format=export_format, **kwargs)
    return output_path


def _video_has_audio(video_path: str) -> bool:
    try:
        res = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                video_path,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return bool(res.stdout.strip())
    except Exception:
        return False


def _mux_video_with_music(video_path: str, music_path: str, output_path: str, transcode_video: bool = False) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    has_audio = _video_has_audio(video_path)
    video_codec = ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p"] if transcode_video else ["-c:v", "copy"]
    cmd = ["ffmpeg", "-y", "-i", video_path, "-i", music_path]

    if has_audio:
        cmd += [
            "-filter_complex",
            "[1:a:0]volume=0.82[music];[0:a:0][music]amix=inputs=2:duration=first:dropout_transition=0[aout]",
            "-map",
            "0:v:0",
            "-map",
            "[aout]",
        ]
    else:
        cmd += ["-map", "0:v:0", "-map", "1:a:0"]

    cmd += video_codec + ["-c:a", "aac", "-b:a", "192k", "-shortest", output_path]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _stderr_text(exc: subprocess.CalledProcessError) -> str:
    if isinstance(exc.stderr, bytes):
        return exc.stderr.decode("utf-8", errors="replace")
    return str(exc.stderr or exc)


def render_video_with_mixed_audio(
    timeline_data: dict,
    bgm_path: Optional[str],
    video_path: str,
    output_path: str,
    custom_sfx_paths: Optional[dict[str, str]] = None,
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=os.path.dirname(output_path))
    tmp_audio_path = tmp.name
    tmp.close()

    try:
        render_mixed_audio(timeline_data, bgm_path, tmp_audio_path, "wav", custom_sfx_paths)
        try:
            _mux_video_with_music(video_path, tmp_audio_path, output_path, transcode_video=False)
        except subprocess.CalledProcessError as copy_exc:
            try:
                _mux_video_with_music(video_path, tmp_audio_path, output_path, transcode_video=True)
            except subprocess.CalledProcessError as transcode_exc:
                raise RuntimeError(
                    "MP4 export failed. "
                    f"copy_stderr={_stderr_text(copy_exc)} "
                    f"transcode_stderr={_stderr_text(transcode_exc)}"
                ) from transcode_exc
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError("MP4 export did not produce a usable file")
        return output_path
    finally:
        if os.path.exists(tmp_audio_path):
            os.remove(tmp_audio_path)


def render_synthetic_bgm(timeline_data: dict, output_path: str, fmt: str = "mp3") -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bgm = _synth_bgm(timeline_data)
    export_format = "mp3" if fmt == "mp3" else fmt
    kwargs = {"bitrate": "320k"} if fmt == "mp3" else {}
    bgm.export(output_path, format=export_format, **kwargs)
    return output_path
