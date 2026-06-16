import os
import logging
import uuid
from sqlalchemy import text
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from .database import engine, Base
from .config import settings
from .routers import auth, video, timeline, generation, export, community, assets

# Import all models so Base.metadata knows about them
from .models import user_model, video_model, timeline_model, generation_model, export_model, community_model, user_asset_model

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BACKEND_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_PATH = os.path.join(LOG_DIR, "musecut.log")
logger = logging.getLogger("musecut")
logger.setLevel(logging.INFO)
if not logger.handlers:
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

app = FastAPI(title="MuseCut AI Music Director API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth.router)
app.include_router(video.router)
app.include_router(timeline.router)
app.include_router(generation.router)
app.include_router(export.router)
app.include_router(community.router)
app.include_router(assets.router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Static files (frontend dist)
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)
FRONTEND_DIST = os.path.join(PROJECT_DIR, "..", "frontend", "dist")
FRONTEND_DIST = os.path.abspath(FRONTEND_DIST)

ASSETS_DIR = os.path.join(FRONTEND_DIST, "assets")
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

for public_dir in ["showcase", "sfx", "learn", "inspiration"]:
    static_dir = os.path.join(FRONTEND_DIST, public_dir)
    if os.path.exists(static_dir):
        app.mount(f"/{public_dir}", StaticFiles(directory=static_dir), name=f"frontend_{public_dir}")


@app.on_event("startup")
async def on_startup():
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()
    # Ensure directories exist
    for directory in [settings.UPLOAD_DIR, settings.EXPORT_DIR, settings.GENERATED_DIR]:
        os.makedirs(directory, exist_ok=True)


def _ensure_sqlite_columns():
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(community_posts)")).fetchall()
        columns = {row[1] for row in rows}
        if "is_anonymous" not in columns:
            conn.execute(text("ALTER TABLE community_posts ADD COLUMN is_anonymous BOOLEAN DEFAULT 0"))

        user_rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        user_columns = {row[1] for row in user_rows}
        if "avatar_url" not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url TEXT DEFAULT ''"))

        export_rows = conn.execute(text("PRAGMA table_info(export_tasks)")).fetchall()
        export_columns = {row[1] for row in export_rows}
        if "error_msg" not in export_columns:
            conn.execute(text("ALTER TABLE export_tasks ADD COLUMN error_msg TEXT DEFAULT ''"))


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/vite.svg")
async def vite_svg():
    path = os.path.join(FRONTEND_DIST, "vite.svg")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return Response(content=f.read(), media_type="image/svg+xml")


@app.exception_handler(StarletteHTTPException)
async def spa_fallback(request: Request, exc: StarletteHTTPException):
    """404 fallback to index.html for SPA routing."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    if exc.status_code == 404 and not request.url.path.startswith("/api"):
        index_path = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "rb") as f:
                return Response(content=f.read(), media_type="text/html")
    return JSONResponse(
        {
            "detail": exc.detail,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
        status_code=exc.status_code,
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception(
        "Unhandled API error request_id=%s method=%s path=%s client=%s error_type=%s error=%s",
        request_id,
        request.method,
        request.url.path,
        request.client.host if request.client else "unknown",
        exc.__class__.__name__,
        str(exc),
    )
    return JSONResponse(
        {
            "detail": {
                "message": "服务器内部错误",
                "request_id": request_id,
                "error_type": exc.__class__.__name__,
                "error": str(exc),
                "hint": f"完整堆栈已记录到 {LOG_PATH}",
            },
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
        status_code=500,
        headers={"X-Request-ID": request_id},
    )
