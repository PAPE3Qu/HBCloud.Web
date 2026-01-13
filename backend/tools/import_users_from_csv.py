import csv
import secrets
import string
import sys
from pathlib import Path
import sqlite3
from time import time

from passlib.context import CryptContext

# 项目根和 data 目录（从脚本位置推导）
TOOLS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TOOLS_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_ROOT = PROJECT_ROOT / 'data'
USERS_DB = DATA_ROOT / 'users.db'

# 与后端一致的密码哈希配置（pbkdf2_sha256）
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def get_db_conn() -> sqlite3.Connection:
    USERS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(USERS_DB)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_users_table():
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                login_failed_count INTEGER NOT NULL DEFAULT 0,
                login_locked_until REAL NOT NULL DEFAULT 0
            );
            """
        )
        # 新增：部门角色表，存储部门空间的管理员/成员关联
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dept_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dept_id TEXT NOT NULL,
                phone TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """
        )
        # 常用查询索引：按部门和角色查询，按手机号查询
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_dept_roles_dept_role ON dept_roles(dept_id, role);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_dept_roles_phone ON dept_roles(phone);"
        )
        conn.commit()
    finally:
        conn.close()


def gen_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def user_exists(phone: str) -> bool:
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE phone=? LIMIT 1", (phone,))
        return cur.fetchone() is not None
    finally:
        conn.close()


def create_user(phone: str, name: str, plain_password: str):
    now = float(time())
    password_hash = pwd_context.hash(plain_password)
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (phone, name, password_hash, role, is_active,
                               created_at, updated_at, login_failed_count, login_locked_until)
            VALUES (?, ?, ?, 'user', 1, ?, ?, 0, 0)
            """,
            (phone, name, password_hash, now, now),
        )
        conn.commit()
    finally:
        conn.close()


def import_from_csv(csv_path: Path):
    if not csv_path.exists():
        print(f"CSV 文件不存在: {csv_path}")
        return

    ensure_users_table()

    print(f"使用数据库: {USERS_DB}")
    print(f"开始从 CSV 导入用户: {csv_path}")
    print("仅支持两列: phone,name   （首行为表头）")
    print("已存在手机号的记录会被跳过。")
    print("-" * 60)

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if "phone" not in reader.fieldnames or "name" not in reader.fieldnames:
            print("CSV 表头必须包含 phone 和 name 两列。")
            return

        created = 0
        skipped = 0

        for row in reader:
            phone = (row.get("phone") or "").strip()
            name = (row.get("name") or "").strip()
            if not phone or not name:
                print(f"跳过：缺少手机号或姓名 -> {row}")
                skipped += 1
                continue

            if user_exists(phone):
                print(f"跳过：手机号已存在 -> {phone} ({name})")
                skipped += 1
                continue

            plain_pwd = gen_password(12)
            create_user(phone, name, plain_pwd)
            created += 1
            print(f"创建用户：{phone} ({name}) 初始密码：{plain_pwd}")

        print("-" * 60)
        print(f"导入完成：成功创建 {created} 个用户，跳过 {skipped} 行。")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python backend/tools/import_users_from_csv.py users.csv")
        sys.exit(1)
    csv_file = Path(sys.argv[1]).resolve()
    import_from_csv(csv_file)