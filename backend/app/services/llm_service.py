import json
import hashlib
import httpx
from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

_cache = {}


def build_prompt(emotion_text: str) -> str:
    return f"""你是一个专业的音乐编曲师。请阅读用户的情绪描述，将其转化为音乐参数。

情绪描述："{emotion_text}"

请严格按以下JSON格式输出（不要输出任何其他内容）：

{{
  "scale": "C_minor",
  "tempo": 72,
  "chord_progression": ["Cm7", "Gm7", "Abmaj7", "Ebmaj7"],
  "rhythm_style": "slow_arpeggio",
  "melody_contour": "descending_gentle",
  "instrument": "piano",
  "mood": "melancholic",
  "description": "一段温柔的描述"
}}

规则：
- scale: 可选值 ["C_major","D_major","E_major","F_major","G_major","A_major","B_major","C_minor","D_minor","E_minor","F_minor","G_minor","A_minor","B_minor","C_dorian","D_dorian","F_dorian","G_dorian"]
- tempo: 40-180 的整数
- chord_progression: 4个和弦的数组，至少用七和弦（m7, maj7, 7, dim7）
- rhythm_style: 可选 ["slow_arpeggio","flowing_arpeggio","gentle_broken_chord","steady_waltz","soft_block","sparse_warm"]
- melody_contour: 可选 ["descending_gentle","ascending_hopeful","wavelike_calm","minimal_sparse","stepwise_warm"]
- instrument: 可选 ["piano","guitar","strings","music_box","warm_pad"]
- mood: 可选 ["melancholic","hopeful","calm","nostalgic","lonely","warm","sad","healing","bittersweet","peaceful"]
- description: 用中文30字以内描述这段音乐的感觉

请根据用户情绪，选出最契合的音乐参数组合。只输出JSON。"""


def generate_params(emotion_text: str) -> dict:
    cache_key = hashlib.md5(emotion_text.encode()).hexdigest()
    if cache_key in _cache:
        return _cache[cache_key]

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个专业的音乐编曲师AI，只输出严格JSON格式的音乐参数。"},
            {"role": "user", "content": build_prompt(emotion_text)}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(DEEPSEEK_BASE_URL, headers=headers, json=payload)

    if resp.status_code != 200:
        return _fallback_params(emotion_text)

    content = resp.json()["choices"][0]["message"]["content"].strip()
    content = content.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(content)
        _validate_params(result)
        _cache[cache_key] = result
        return result
    except (json.JSONDecodeError, ValueError):
        return _fallback_params(emotion_text)


def _validate_params(params: dict):
    valid_instruments = {"piano", "guitar", "strings", "music_box", "warm_pad"}
    if params.get("instrument") not in valid_instruments:
        params["instrument"] = "piano"
    tempo = params.get("tempo", 72)
    params["tempo"] = max(40, min(180, int(tempo)))
    if len(params.get("chord_progression", [])) < 2:
        params["chord_progression"] = ["Am7", "Fmaj7", "C7", "G7"]


def _fallback_params(emotion_text: str) -> dict:
    text = emotion_text.lower()
    if any(w in text for w in ["悲伤", "伤心", "难过", "痛苦", "泪", "sad", "pain"]):
        mood = "sad"
        scale = "D_minor"
        tempo = 60
        chords = ["Dm7", "Gm7", "Bbmaj7", "Am7"]
    elif any(w in text for w in ["希望", "阳光", "温暖", "快乐", "happy", "hope"]):
        mood = "hopeful"
        scale = "C_major"
        tempo = 100
        chords = ["Cmaj7", "Am7", "Fmaj7", "G7"]
    elif any(w in text for w in ["思念", "回忆", "怀念", "nostalgia"]):
        mood = "nostalgic"
        scale = "F_dorian"
        tempo = 78
        chords = ["Fm7", "Ebmaj7", "Dbmaj7", "Cm7"]
    elif any(w in text for w in ["平静", "安静", "宁静", "calm", "peace"]):
        mood = "calm"
        scale = "G_major"
        tempo = 65
        chords = ["Gmaj7", "Em7", "Cmaj7", "D7"]
    else:
        mood = "melancholic"
        scale = "A_minor"
        tempo = 72
        chords = ["Am7", "Fmaj7", "C7", "G7"]

    return {
        "scale": scale, "tempo": tempo,
        "chord_progression": chords, "rhythm_style": "flowing_arpeggio",
        "melody_contour": "wavelike_calm", "instrument": "piano",
        "mood": mood, "description": "一段来自心底的旋律"
    }
