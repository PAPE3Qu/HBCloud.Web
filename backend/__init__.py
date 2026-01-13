from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from .config import DATA_ROOT

from . import routers  # noqa: F401
from .routers import auth, users, files, home, feedbacks, audit, share_links

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 文件管理相关接口
app.include_router(files.router, prefix="/api/files", tags=["files"])
# 首页公告
app.include_router(home.router)
# 留言反馈
app.include_router(feedbacks.router)
# 审计
app.include_router(audit.router)
# 分享短码相关接口（/api/share）
app.include_router(share_links.router, prefix="/api", tags=["share"])
# 认证与用户管理
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])


def _init_users_db():
    """初始化 users.db：确保 user_quick_access 表存在。

    与 backend.main 中的逻辑保持一致，
    以兼容通过 `uvicorn backend.__init__:app` 启动的场景。
    """
    db_path = DATA_ROOT / "users.db"
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_quick_access (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              owner_phone   TEXT NOT NULL,
              target_phone  TEXT NOT NULL,
              target_name   TEXT NOT NULL,
              sort_order    INTEGER NOT NULL DEFAULT 0,
              created_at    INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_quick_access_owner
              ON user_quick_access(owner_phone)
            """
        )
        conn.commit()
    finally:
        conn.close()


# 在应用创建后立即初始化 users.db
_init_users_db()


@app.get("/")
def read_root():
    return {"status": "ok"}