from fastapi import APIRouter
from ..schemas.llm import EmotionInput
from ..services.llm_service import generate_params

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.post("/generate-params")
def generate_music_params(data: EmotionInput):
    params = generate_params(data.emotion_text)
    return params
