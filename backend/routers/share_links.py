from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import time
import string
import random
from ..config import DATA_ROOT
from ..services.files.base import write_log
from .auth import get_current_user
from .audit import append_audit_record, AuditRecord

router = APIRouter()

DB_PATH = DATA_ROOT / 'share_links.db'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS share_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                share_id TEXT NOT NULL UNIQUE,
                created_ts REAL NOT NULL,
                expire_ts REAL,
                space_type TEXT NOT NULL,
                department_id TEXT,
                path TEXT NOT NULL,
                anchor_name TEXT,
                selected_names_json TEXT NOT NULL
            );
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_share_links_share_id ON share_links(share_id);"
        )
        conn.commit()
    finally:
        conn.close()


_init_db()


class CreateShareBody(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str = ''
    anchorName: Optional[str] = None
    selectedNames: List[str] = []
    # 预留：是否设置过期时间（秒）；目前前端不使用，可选
    expireSeconds: Optional[int] = None


class ShareInfo(BaseModel):
    shareId: str
    spaceType: str
    departmentId: Optional[str] = None
    path: str = ''
    anchorName: Optional[str] = None
    selectedNames: List[str] = []


def _gen_share_id(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(random.choice(alphabet) for _ in range(length))


def _create_unique_share_id(conn: sqlite3.Connection, max_retry: int = 5) -> str:
    cur = conn.cursor()
    for _ in range(max_retry):
        sid = _gen_share_id()
        cur.execute("SELECT 1 FROM share_links WHERE share_id = ?", (sid,))
        if not cur.fetchone():
            return sid
    # 退而求其次：加时间戳后缀，极端情况下保证唯一
    return _gen_share_id(8) + str(int(time.time()))[-4:]


@router.post('/share', response_model=ShareInfo)
async def create_share(body: CreateShareBody, request: Request, current_user: dict = Depends(get_current_user)):
    """创建分享短码：返回 shareId 及原始上下文。

    - 仅负责生成/保存 shareId，不做权限校验；
    - 审计日志在此接口内部统一记录。
    """
    now = time.time()
    expire_ts = None
    if body.expireSeconds and body.expireSeconds > 0:
        expire_ts = now + int(body.expireSeconds)

    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        share_id = _create_unique_share_id(conn)
        import json

        cur.execute(
            """
            INSERT INTO share_links (
                share_id, created_ts, expire_ts,
                space_type, department_id, path,
                anchor_name, selected_names_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                share_id,
                now,
                expire_ts,
                body.spaceType,
                (body.departmentId or None),
                body.path or '',
                body.anchorName,
                json.dumps(body.selectedNames or [], ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    client_ip = request.client.host if request.client else ""
    creator_phone = (current_user.get("phone") or "") if current_user else ""

    # 文本日志
    write_log(
        "share_create id=%s space=%s dept=%s path=%s names=%s expire=%s by=%s ip=%s"
        % (
            share_id,
            body.spaceType,
            body.departmentId or "",
            body.path or "",
            ",".join(body.selectedNames or []),
            str(expire_ts or ""),
            creator_phone,
            client_ip,
        )
    )

    # 审计日志
    append_audit_record(
        AuditRecord(
            ts=time.time(),
            action="share",
            path=body.path or "",
            spaceType=body.spaceType,
            departmentId=body.departmentId or None,
            clientIp=client_ip,
            detail={
                "event": "create_share",
                "shareId": share_id,
                "spaceType": body.spaceType,
                "departmentId": body.departmentId or None,
                "path": body.path or "",
                "anchorName": body.anchorName,
                "selectedNames": body.selectedNames or [],
                "expireSeconds": body.expireSeconds,
                "createdBy": creator_phone,
            },
        )
    )

    return ShareInfo(
        shareId=share_id,
        spaceType=body.spaceType,
        departmentId=body.departmentId or None,
        path=body.path or '',
        anchorName=body.anchorName,
        selectedNames=body.selectedNames or [],
    )


@router.get('/share/{share_id}', response_model=ShareInfo)
async def get_share(share_id: str):
    """根据 shareId 还原分享上下文。

    - 如设置了过期时间且已过期，则返回 404；
    - 无记录同样返回 404。
    """
    now = time.time()
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT share_id, created_ts, expire_ts,
                   space_type, department_id, path,
                   anchor_name, selected_names_json
            FROM share_links
            WHERE share_id = ?
            """,
            (share_id,),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail='share_not_found')

    expire_ts = row['expire_ts']
    if expire_ts is not None and float(expire_ts) > 0 and now > float(expire_ts):
        raise HTTPException(status_code=404, detail='share_expired')

    import json

    try:
        names = json.loads(row['selected_names_json'] or '[]')
    except Exception:
        names = []

    return ShareInfo(
        shareId=row['share_id'],
        spaceType=row['space_type'],
        departmentId=row['department_id'],
        path=row['path'] or '',
        anchorName=row['anchor_name'],
        selectedNames=names,
    )
