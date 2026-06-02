from pydantic import BaseModel


class EmotionInput(BaseModel):
    emotion_text: str


class MusicParamsResponse(BaseModel):
    scale: str
    tempo: int
    chord_progression: list
    rhythm_style: str
    melody_contour: str
    instrument: str
    mood: str
    description: str = ""
