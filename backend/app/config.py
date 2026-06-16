import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Timeline LLM
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "glm")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", os.getenv("GLM_MODEL", "glm-4-flash"))

    # 智谱 GLM-4-Flash API
    GLM_API_KEY: str = os.getenv("GLM_API_KEY", "")
    GLM_MODEL: str = os.getenv("GLM_MODEL", "glm-4-flash")

    # ACE-Step API
    ACESTEP_API_URL: str = os.getenv("ACESTEP_API_URL", "http://localhost:8001")
    ACESTEP_MOCK_MODE: str = os.getenv("ACESTEP_MOCK_MODE", "auto")

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "musecut_jwt_secret_key_2026")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./musecut.db")

    # Storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    EXPORT_DIR: str = os.getenv("EXPORT_DIR", "exports")
    GENERATED_DIR: str = os.getenv("GENERATED_DIR", "generated")


settings = Settings()
