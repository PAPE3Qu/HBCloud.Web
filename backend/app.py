from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from routers import files as files_router

app = FastAPI(title="HBCloud Disk", version="0.1.0")

# CORS 设置，便于前端开发调试
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件目录（用于托管前端构建后的文件）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 文件接口统一挂载到 /api/files 前缀，保持与 main.py 一致
app.include_router(files_router.router, prefix="/api/files", tags=["files"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


# 前端单页应用入口（当有前端构建结果后，返回 index.html）
@app.get("/")
async def index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "HBCloud Disk backend is running. For full API please run 'uvicorn main:app' and build frontend into backend/static."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
