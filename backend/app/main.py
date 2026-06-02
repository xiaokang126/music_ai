import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .database import engine, Base
from .routers import auth, works, comments, llm, diary, healing, gifts, resonance

Base.metadata.create_all(bind=engine)

app = FastAPI(title="失恋广场 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由
app.include_router(auth.router)
app.include_router(works.router)
app.include_router(comments.router)
app.include_router(llm.router)
app.include_router(diary.router)
app.include_router(healing.router)
app.include_router(gifts.router)
app.include_router(resonance.router)

# 前端静态文件 - 使用绝对路径
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))  # .../backend/app
PROJECT_DIR = os.path.dirname(BACKEND_DIR)  # .../backend
FRONTEND_DIST = os.path.join(PROJECT_DIR, "..", "frontend", "dist")
FRONTEND_DIST = os.path.abspath(FRONTEND_DIST)

ASSETS_DIR = os.path.join(FRONTEND_DIST, "assets")
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/vite.svg")
def vite_svg():
    path = os.path.join(FRONTEND_DIST, "vite.svg")
    if os.path.exists(path):
        return FileResponse(path, media_type="image/svg+xml")
    return {"detail": "Not Found"}, 404


@app.get("/{full_path:path}")
async def serve_spa(full_path: str, request: Request):
    if full_path.startswith("api/"):
        return {"detail": "Not Found"}, 404
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "请先构建前端: cd frontend && npm run build"}
