from fastapi import FastAPI
from routers import files, home, feedbacks, audit
from routers import share_links
from routers import auth, users  # 新增认证与用户管理路由
from routers import shortcut
import sqlite3
from .config import DATA_ROOT

app = FastAPI()

# 文件管理相关接口，统一挂载到 /api/files 前缀
app.include_router(files.router, prefix="/api/files", tags=["files"])

# 快捷方式相关接口
app.include_router(shortcut.router, prefix="/api/shortcut", tags=["shortcut"])

# 首页公告相关接口
app.include_router(home.router)

# 留言反馈相关接口
app.include_router(feedbacks.router)

# 审计相关接口
app.include_router(audit.router)

# 分享短码相关接口（/api/share）
app.include_router(share_links.router, prefix="/api", tags=["share"])

# 用户认证与管理
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])

def _init_users_db():
    """初始化 users.db：目前仅确保 user_quick_access 表存在。

    - 仅在应用启动时调用一次。
    - 若表已存在则不会抛错。
    """
    db_path = DATA_ROOT / "users.db"
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # 创建 user_quick_access 表（若不存在）
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


# 在应用创建时调用初始化
_init_users_db()