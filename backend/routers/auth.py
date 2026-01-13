from datetime import datetime, timedelta, time
import json
from pathlib import Path
import sqlite3
from typing import Optional, Dict, Any, Tuple, List

from fastapi import APIRouter, HTTPException, Depends, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext

from ..config import ADMIN_INVITE_CODE, SUPER_ADMIN_USERNAME, SUPER_ADMIN_PASSWORD, DATA_ROOT
from ..services.files.base import write_log  # 新增：复用统一文本日志
from .audit import append_audit_record, AuditRecord  # 新增：结构化审计

router = APIRouter()

USERS_DB = DATA_ROOT / "users.db"
USERS_DB.parent.mkdir(parents=True, exist_ok=True)

# 使用 pbkdf2_sha256 替代 bcrypt，避免当前环境的 bcrypt 兼容问题
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer(auto_error=False)

JWT_SECRET = "hbcloud-secret"
JWT_ALG = "HS256"

# 简单基于内存的登录失败计数与锁定信息（如已存在类似结构，则合并逻辑）
_login_failures: Dict[str, Dict[str, Any]] = {}
LOCK_THRESHOLD = 5
LOCK_MINUTES = 5


def _get_db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(USERS_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _init_users_db():
    conn = _get_db_conn()
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
        conn.commit()
    finally:
        conn.close()


_init_users_db()


def _is_account_locked(username: str) -> Tuple[bool, int]:
    info = _login_failures.get(username)
    if not info:
        return False, 0
    lock_until = info.get('lock_until')
    if lock_until and lock_until > datetime.utcnow():
        # 返回剩余秒数用于提示
        remain = int((lock_until - datetime.utcnow()).total_seconds())
        return True, max(remain, 0)
    return False, 0


def _record_login_failure(username: str):
    now = datetime.utcnow()
    info = _login_failures.get(username) or {'count': 0, 'lock_until': None, 'last_fail': now}
    locked, _ = _is_account_locked(username)
    if locked:
        info['count'] += 1
        info['last_fail'] = now
        _login_failures[username] = info
        # 已在锁定期内再次失败，写一条失败日志
        write_log(f"auth_login_failed phone={username} count={info['count']} status=locked_in_memory")
        return
    # 未锁定：累加错误计数
    info['count'] = info.get('count', 0) + 1
    info['last_fail'] = now
    if info['count'] >= LOCK_THRESHOLD:
        info['lock_until'] = now + timedelta(minutes=LOCK_MINUTES)
        # 达到阈值，写锁定日志
        write_log(
            f"auth_account_locked_in_memory phone={username} failCount={info['count']} lockMinutes={LOCK_MINUTES}"
        )
    _login_failures[username] = info


def _reset_login_counter_on_success(username: str):
    info = _login_failures.get(username)
    if not info:
        return
    # 成功登录时，只清理错误计数，但不移除 lock_until，保证锁定时间按自然时间持续
    info['count'] = 0
    _login_failures[username] = info


def _load_users() -> List[Dict[str, Any]]:
    """从 SQLite 读取全部用户，用于 ensure_super_admin 等少量场景。"""
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, phone, name, password_hash, role, is_active, created_at, updated_at, login_failed_count, login_locked_until FROM users")
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _now_ts() -> float:
    return datetime.utcnow().timestamp()


def _get_next_id(users: List[Dict[str, Any]]) -> int:
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT MAX(id) FROM users")
        row = cur.fetchone()
        max_id = row[0] or 0
        return max_id + 1
    finally:
        conn.close()


def _find_user_by_phone(phone: str) -> Optional[dict]:
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, phone, name, password_hash, role, is_active, created_at, updated_at, login_failed_count, login_locked_until FROM users WHERE phone = ?",
            (phone,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _get_user_by_id(user_id: int) -> Optional[dict]:
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, phone, name, password_hash, role, is_active, created_at, updated_at, login_failed_count, login_locked_until FROM users WHERE id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _update_user(user: dict) -> None:
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE users
            SET phone = ?, name = ?, password_hash = ?, role = ?, is_active = ?,
                created_at = ?, updated_at = ?, login_failed_count = ?, login_locked_until = ?
            WHERE id = ?
            """,
            (
                user.get("phone"),
                user.get("name"),
                user.get("password_hash"),
                user.get("role", "user"),
                1 if user.get("is_active", True) else 0,
                float(user.get("created_at") or 0),
                float(user.get("updated_at") or 0),
                int(user.get("login_failed_count") or 0),
                float(user.get("login_locked_until") or 0),
                int(user.get("id")),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_user(user: dict) -> dict:
    """插入新用户并返回带 id 的完整记录。"""
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (phone, name, password_hash, role, is_active, created_at, updated_at, login_failed_count, login_locked_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.get("phone"),
                user.get("name"),
                user.get("password_hash"),
                user.get("role", "user"),
                1 if user.get("is_active", True) else 0,
                float(user.get("created_at") or 0),
                float(user.get("updated_at") or 0),
                int(user.get("login_failed_count") or 0),
                float(user.get("login_locked_until") or 0),
            ),
        )
        user_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()
    created = _get_user_by_id(user_id)
    return created or user


def _ensure_super_admin():
    users = _load_users()
    if any(u.get("role") == "super" for u in users):
        return
    now = _now_ts()
    admin_user = {
        "phone": SUPER_ADMIN_USERNAME,
        "name": "超级管理员",
        "password_hash": pwd_context.hash(SUPER_ADMIN_PASSWORD),
        "role": "super",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "login_failed_count": 0,
        "login_locked_until": 0,
    }
    _insert_user(admin_user)


_ensure_super_admin()


def _create_token(user: dict) -> str:
    now = datetime.utcnow()
    expire_at = now + timedelta(hours=24)
    payload = {
        "sub": str(user["id"]),
        "phone": user["phone"],
        "name": user.get("name") or "",
        "role": user.get("role") or "user",
        "login_date": now.date().isoformat(),
        "exp": int(expire_at.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None,
) -> dict:
    token = None
    # 优先从 cookie 读取 hb_token（前端大部分请求依赖 HttpOnly cookie）
    if request is not None:
        token = request.cookies.get("hb_token")
    # 如显式提供了 Authorization Bearer，则以其为准
    if credentials is not None and credentials.credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(status_code=401, detail="not_authenticated")

    try:
        # 使用默认exp校验，过期会抛出JWTError
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        raise HTTPException(status_code=401, detail="invalid_token")

    user_id = int(payload.get("sub", 0))
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid_token_payload")

    user = _get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="user_not_found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="user_inactive")
    return user


@router.post("/register")
def register(payload: dict, request: Request):
    phone = (payload.get("phone") or "").strip()
    name = (payload.get("name") or "").strip()
    invite = (payload.get("invite_code") or "").strip()
    password = payload.get("password") or ""
    password2 = payload.get("password_confirm") or ""

    client_ip = request.client.host if request.client else ""

    if not phone or not name or not invite or not password or not password2:
        raise HTTPException(status_code=400, detail="missing_required_fields")
    if invite != ADMIN_INVITE_CODE:
        # 记录一次非法邀请码尝试（不包含密码）
        write_log(f"auth_register_invite_invalid phone={phone} ip={client_ip}")
        raise HTTPException(status码=400, detail="invalid_invite_code")
    if password != password2:
        raise HTTPException(status码=400, detail="password_mismatch")

    if _find_user_by_phone(phone):
        raise HTTPException(status码=409, detail="phone_already_registered")

    now = _now_ts()
    user = {
        "phone": phone,
        "name": name,
        "password_hash": pwd_context.hash(password),
        "role": "user",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "login_failed_count": 0,
        "login_locked_until": 0,
    }
    user = _insert_user(user)

    # 注册成功日志
    write_log(f"auth_register_success phone={phone} ip={client_ip}")

    token = _create_token(user)
    resp_user = {"id": user["id"], "phone": phone, "name": name, "role": user["role"]}

    # 审计：注册成功
    append_audit_record(
        AuditRecord(
            ts=datetime.utcnow().timestamp(),
            action="auth",
            path="/auth/register",
            spaceType="",
            departmentId=None,
            clientIp=client_ip,
            detail={
                "event": "register",
                "phone": phone,
                "role": user["role"],
            },
        )
    )

    return {"token": token, "user": resp_user}


@router.post("/login")
def login(payload: dict, response: Response, request: Request):
    phone = (payload.get("phone") or "").strip()
    password = payload.get("password") or ""
    client_ip = request.client.host if request.client else ""
    if not phone or not password:
        raise HTTPException(status码=400, detail="手机号未注册/账号或密码错误")

    user = _find_user_by_phone(phone)
    if not user:
        # 未注册账号尝试登录
        write_log(f"auth_login_failed phone={phone} ip={client_ip} reason=not_registered")
        raise HTTPException(status码=401, detail="手机号未注册/账号或密码错误")

    locked, remain = _is_account_locked(phone)
    if locked:
        write_log(
            f"auth_login_blocked_by_memory_lock phone={phone} ip={client_ip} remainSeconds={remain}"
        )
        raise HTTPException(
            status码=403,
            detail="手机号未注册/账号或密码错误",
        )

    now_ts = _now_ts()
    locked_until = float(user.get("login_locked_until") or 0)
    if locked_until and now_ts < locked_until:
        write_log(
            f"auth_login_blocked_by_db_lock phone={phone} ip={client_ip} until={locked_until}"
        )
        raise HTTPException(status码=423, detail="手机号未注册/账号或密码错误")

    if not pwd_context.verify(password, user.get("password_hash") or ""):
        _record_login_failure(phone)
        info = _login_failures.get(phone)
        if info and info.get('lock_until') and info['lock_until'] > datetime.utcnow():
            write_log(
                f"auth_login_failed_and_locked phone={phone} ip={client_ip} failCount={info.get('count', 0)}"
            )
            raise HTTPException(status码=403, detail="手机号未注册/账号或密码错误")
        write_log(
            f"auth_login_failed phone={phone} ip={client_ip} reason=wrong_password"
        )
        raise HTTPException(status码=401, detail="手机号未注册/账号或密码错误")

    # 登录成功
    _reset_login_counter_on_success(phone)
    user["login_failed_count"] = 0
    user["login_locked_until"] = 0
    user["updated_at"] = now_ts
    _update_user(user)

    token = _create_token(user)
    response.set_cookie(
        key="hb_token",
        value=token,
        httponly=True,
        max_age=24 * 3600,
        path="/",
    )

    # 文本日志
    write_log(f"auth_login_success phone={phone} ip={client_ip}")

    # 审计日志
    append_audit_record(
        AuditRecord(
            ts=datetime.utcnow().timestamp(),
            action="auth",
            path="/auth/login",
            spaceType="",
            departmentId=None,
            clientIp=client_ip,
            detail={
                "event": "login",
                "phone": phone,
                "role": user.get("role") or "user",
            },
        )
    )

    resp_user = {"id": user["id"], "phone": user["phone"], "name": user.get("name") or "", "role": user.get("role") or "user"}
    return {"token": token, "user": resp_user}


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {"id": current_user["id"], "phone": current_user["phone"], "name": current_user.get("name") or "", "role": current_user.get("role") or "user"}


@router.post("/change-password")
def change_password(payload: dict, request: Request):
    """修改密码接口：无需已登录，但必须提供手机号和原密码。

    请求体：{ phone, old_password, new_password, new_password_confirm }
    - 若忘记密码，请联系系统管理员重置。
    """
    phone = (payload.get("phone") or "").strip()
    old_pwd = payload.get("old_password") or ""
    new_pwd = payload.get("new_password") or ""
    new_pwd2 = payload.get("new_password_confirm") or ""

    if not phone or not old_pwd or not new_pwd or not new_pwd2:
        raise HTTPException(status码=400, detail="missing_required_fields")
    if new_pwd != new_pwd2:
        raise HTTPException(status码=400, detail="password_mismatch")

    user = _find_user_by_phone(phone)
    if not user:
        raise HTTPException(status码=404, detail="user_not_found")

    if not pwd_context.verify(old_pwd, user.get("password_hash") or ""):
        raise HTTPException(status码=401, detail="invalid_old_password")

    now = _now_ts()
    user["password_hash"] = pwd_context.hash(new_pwd)
    user["updated_at"] = now
    user["login_failed_count"] = 0
    user["login_locked_until"] = 0
    _update_user(user)

    client_ip = request.client.host if request.client else ""
    # 文本日志
    write_log(f"auth_change_password_success phone={phone} ip={client_ip}")
    # 审计日志
    append_audit_record(
        AuditRecord(
            ts=datetime.utcnow().timestamp(),
            action="auth",
            path="/auth/change-password",
            spaceType="",
            departmentId=None,
            clientIp=client_ip,
            detail={
                "event": "change_password",
                "phone": phone,
            },
        )
    )

    return {"success": True}
