from fastapi import APIRouter, Request, Query
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import time
import sqlite3
from ..config import DATA_ROOT
from datetime import datetime
from ..services.files.base import write_log  # 新增导入，用于写人类可读日志

router = APIRouter(prefix="/api/audit", tags=["audit"])

# 日志文件改为单独目录 data/audit_logs/audit.log
AUDIT_LOG_DIR = DATA_ROOT / 'audit_logs'
AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = AUDIT_LOG_DIR / 'audit.log'

# 文件详情数据库保持原有路径 data/audit_index/file_detail.db
DB_PATH = DATA_ROOT / 'audit_index' / 'file_detail.db'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

MAX_AUDIT_SIZE = 5 * 1024 * 1024  # 约 5MB


def _get_db_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    """初始化文件详情索引库：用于实时维护下载次数、最后访问/编辑信息。

    仅用于当前版本起的新数据，历史数据不做回放重建。
    """
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS file_detail (
                spaceType TEXT NOT NULL,
                departmentId TEXT,
                path TEXT NOT NULL,
                name TEXT NOT NULL,
                downloadCount INTEGER NOT NULL DEFAULT 0,
                lastAccessTs REAL,
                lastEditUser TEXT,
                lastEditTs REAL,
                PRIMARY KEY (spaceType, departmentId, path, name)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


_init_db()


class AuditRecord(BaseModel):
    ts: float
    action: str
    path: str
    spaceType: str
    departmentId: Optional[str] = None
    clientIp: str = ''
    detail: Dict[str, Any] = {}


class AuditQueryResponse(BaseModel):
    items: List[AuditRecord]


class FileStat(BaseModel):
    path: str
    spaceType: str
    departmentId: Optional[str] = None
    downloadCount: int
    lastAccess: Optional[float] = None


class FileStatResponse(BaseModel):
    items: List[FileStat]


# 新增：文件详情模型，供前端详情面板查询
class FileDetail(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str
    name: str
    downloadCount: int = 0
    lastAccessTs: Optional[float] = None
    lastEditUser: Optional[str] = None
    lastEditTs: Optional[float] = None


class FileDetailResponse(BaseModel):
    item: Optional[FileDetail] = None


# 新增：统一的日志接口，供其他模块调用

def log_action(
    *,
    action: str,
    path: str = "",
    spaceType: str = "",
    departmentId: Optional[str] = None,
    clientIp: str = "",
    detail: Optional[Dict[str, Any]] = None,
    text_message: Optional[str] = None,
) -> None:
    """统一记录一条操作日志：

    - 写入结构化审计日志 audit.log（JSON 每行一条），用于前端审计列表、统计。
    - 写入人类可读文本日志 data/log/YYYY-MM-DD.log，便于人工排查问题。

    说明：
    - 不修改/依赖 file_detail 索引库，保持现有下载次数、编辑人等逻辑不变；
    - 任何异常都被吞掉，不影响主业务流程；
    - 现有直接调用 append_audit_record 的地方仍然可用，后续可逐步切换为 log_action。
    """
    ts = time.time()

    # 组装 detail，冗余一个 isoTime，便于人工阅读 JSON
    d: Dict[str, Any] = {}
    if detail:
        try:
            d.update(detail)
        except Exception:
            # detail 不是映射类型时避免报错
            d["_raw_detail"] = detail  # type: ignore[assignment]
    try:
        d.setdefault("isoTime", datetime.fromtimestamp(ts).isoformat(timespec="seconds"))
    except Exception:
        # 极端情况下时间转换失败也不影响主流程
        pass

    try:
        rec = AuditRecord(
            ts=ts,
            action=action,
            path=path or "",
            spaceType=spaceType or "",
            departmentId=departmentId or None,
            clientIp=clientIp or "",
            detail=d,
        )
        append_audit_record(rec)
    except Exception:
        # 写审计失败不影响业务
        pass

    # 写人类可读文本日志
    try:
        if text_message:
            msg = text_message
        else:
            # 默认简单格式，方便 grep： [action] space=... dept=... path=... detail=JSON
            safe_detail = {}
            try:
                safe_detail = d
            except Exception:
                safe_detail = {"_repr": str(d)}
            msg = (
                f"[{action}] space={spaceType or ''} dept={departmentId or ''} "
                f"path={path or ''} clientIp={clientIp or ''} "
                f"detail={json.dumps(safe_detail, ensure_ascii=False)}"
            )
        write_log(msg)
    except Exception:
        # 文本日志失败也不影响业务
        pass


def _rotate_audit_log_if_needed():
    """如果 audit.log 过大，则进行简单的轮转：
    - 当前 audit.log 重命名为 audit_YYYYMMDD_HHMMSS.log
    - 新建空的 audit.log 继续写入
    """
    if not LOG_PATH.exists():
        return
    try:
        if LOG_PATH.stat().st_size < MAX_AUDIT_SIZE:
            return
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = LOG_PATH.with_name(f'audit_{ts}.log')
        LOG_PATH.rename(backup)
    except Exception:
        # 轮转失败不影响后续写入
        pass


def append_audit_record(rec: AuditRecord):
    """追加一条审计记录到 audit.log，必要时做简单轮转。"""
    _rotate_audit_log_if_needed()
    try:
        line = rec.model_dump_json()
    except AttributeError:
        # 兼容旧版本 Pydantic
        line = json.dumps(rec.dict(), ensure_ascii=False)
    with LOG_PATH.open('a', encoding='utf-8') as f:
        f.write(line + '\n')


def _iter_raw_records():
    if not LOG_PATH.exists():
        return
    with LOG_PATH.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                yield AuditRecord(**data)
            except Exception:
                continue


# ------------- 文件详情索引维护函数（供 files.py 调用） -------------


def _norm_path(path: str) -> str:
    if not path or path in ('.', './'):
        return ''
    # 统一用 posix 风格，去掉首尾 '/'
    p = Path(path).as_posix().strip('/')
    return p


def _ensure_file_row(spaceType: str, departmentId: Optional[str], path: str, name: str):
    """确保文件在索引中存在一行，不存在则以 0 次下载、无编辑信息初始化。

    path 为目录相对空间根目录的路径，不包含文件名。
    """
    space = spaceType
    dept = departmentId or None
    dir_path = _norm_path(path)
    fname = name
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO file_detail
            (spaceType, departmentId, path, name, downloadCount, lastAccessTs, lastEditUser, lastEditTs)
            VALUES (?, ?, ?, ?, 0, NULL, NULL, NULL)
            """,
            (space, dept, dir_path, fname),
        )
        conn.commit()
    finally:
        conn.close()


def touch_download_meta(spaceType: str, departmentId: Optional[str], path: str, name: str, ts: Optional[float] = None):
    """记录一次下载/被打包下载：
    - downloadCount +1
    - lastAccessTs 更新为本次时间
    - 若不存在则自动初始化
    """
    t = ts or time.time()
    space = spaceType
    dept = departmentId or None
    dir_path = _norm_path(path)
    fname = name
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        # 先确保存在
        cur.execute(
            """
            INSERT OR IGNORE INTO file_detail
            (spaceType, departmentId, path, name, downloadCount, lastAccessTs, lastEditUser, lastEditTs)
            VALUES (?, ?, ?, ?, 0, NULL, NULL, NULL)
            """,
            (space, dept, dir_path, fname),
        )
        # 再更新下载次数和最后访问时间
        cur.execute(
            """
            UPDATE file_detail
            SET downloadCount = downloadCount + 1,
                lastAccessTs = ?
            WHERE spaceType = ? AND departmentId IS ? AND path = ? AND name = ?
            """,
            (t, space, dept, dir_path, fname),
        )
        conn.commit()
    finally:
        conn.close()


def touch_edit_meta(spaceType: str, departmentId: Optional[str], path: str, name: str, editor: Optional[str], ts: Optional[float] = None):
    """记录一次编辑行为（上传、重命名、移动、复制、删除前的目标等）：
    - 不改变下载次数
    - 更新 lastEditUser / lastEditTs
    - 若不存在则自动初始化
    """
    t = ts or time.time()
    space = spaceType
    dept = departmentId or None
    dir_path = _norm_path(path)
    fname = name
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO file_detail
            (spaceType, departmentId, path, name, downloadCount, lastAccessTs, lastEditUser, lastEditTs)
            VALUES (?, ?, ?, ?, 0, NULL, NULL, NULL)
            """,
            (space, dept, dir_path, fname),
        )
        cur.execute(
            """
            UPDATE file_detail
            SET lastEditUser = ?,
                lastEditTs = ?
            WHERE spaceType = ? AND departmentId IS ? AND path = ? AND name = ?
            """,
            (editor, t, space, dept, dir_path, fname),
        )
        conn.commit()
    finally:
        conn.close()


def delete_meta(spaceType: str, departmentId: Optional[str], path: str, name: str):
    """删除索引中的一条记录：用于物理删除文件后彻底抹除详情。"""
    space = spaceType
    dept = departmentId or None
    dir_path = _norm_path(path)
    fname = name
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM file_detail
            WHERE spaceType = ? AND departmentId IS ? AND path = ? AND name = ?
            """,
            (space, dept, dir_path, fname),
        )
        conn.commit()
    finally:
        conn.close()


def move_or_rename_meta(
    old_spaceType: str,
    old_departmentId: Optional[str],
    old_path: str,
    old_name: str,
    new_spaceType: str,
    new_departmentId: Optional[str],
    new_path: str,
    new_name: str,
):
    """在索引中移动/重命名一条记录（支持跨空间/部门）：
    - 保留下载次数、最后访问时间、最后编辑信息；
    - 旧记录不存在则忽略（视为新文件，由后续 touch_edit_meta 初始化）。
    """
    old_space = old_spaceType
    old_dept = old_departmentId or None
    new_space = new_spaceType
    new_dept = new_departmentId or None
    old_dir = _norm_path(old_path)
    new_dir = _norm_path(new_path)
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        # 将旧记录迁移到新位置，如存在冲突则覆盖新位置
        cur.execute(
            """
            INSERT INTO file_detail (spaceType, departmentId, path, name, downloadCount, lastAccessTs, lastEditUser, lastEditTs)
            SELECT ?, ?, ?, ?, downloadCount, lastAccessTs, lastEditUser, lastEditTs
            FROM file_detail
            WHERE spaceType = ? AND departmentId IS ? AND path = ? AND name = ?
            ON CONFLICT(spaceType, departmentId, path, name) DO UPDATE SET
                downloadCount = excluded.downloadCount,
                lastAccessTs = excluded.lastAccessTs,
                lastEditUser = excluded.lastEditUser,
                lastEditTs = excluded.lastEditTs
            """,
            (new_space, new_dept, new_dir, new_name, old_space, old_dept, old_dir, old_name),
        )
        # 删除旧位置记录
        cur.execute(
            """
            DELETE FROM file_detail
            WHERE spaceType = ? AND departmentId IS ? AND path = ? AND name = ?
            """,
            (old_space, old_dept, old_dir, old_name),
        )
        conn.commit()
    finally:
        conn.close()


def delete_meta_by_department(spaceType: str, departmentId: str) -> int:
    """删除某个部门空间下的所有 file_detail 索引记录。

    用于：部门被删除（软删除/进回收站）时，联动清理文件详情索引，避免残留。
    返回删除行数。
    """
    dept = (departmentId or '').strip() or None
    if not dept:
        return 0
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM file_detail
            WHERE spaceType = ? AND departmentId IS ?
            """,
            (spaceType, dept),
        )
        conn.commit()
        return int(cur.rowcount or 0)
    finally:
        conn.close()


# ------------- 供前端调用的详情查询接口 -------------


@router.get('/file-detail', response_model=FileDetailResponse)
async def get_file_detail(
    spaceType: str = Query(..., description="空间类型：public/department/safe"),
    departmentId: Optional[str] = Query(None, description="部门ID，可为空"),
    path: str = Query('', description="相对于空间根目录的目录路径（不含文件名），如 '' 或 'docs/sub' 或 '.'"),
    name: str = Query(..., description="文件名"),
):
    """返回单个文件的统计详情：下载次数、最后访问时间、最后编辑人/时间。

    - 仅管理当前版本以来的索引数据；
    - 若不存在记录，则返回 item = null，前端可视为 0 次下载、无访问/编辑信息。
    """
    space = spaceType
    dept = departmentId or None
    dir_path = _norm_path(path)
    fname = name
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT spaceType, departmentId, path, name, downloadCount, lastAccessTs, lastEditUser, lastEditTs
            FROM file_detail
            WHERE spaceType = ? AND departmentId IS ? AND path = ? AND name = ?
            """,
            (space, dept, dir_path, fname),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return FileDetailResponse(item=None)

    item = FileDetail(
        spaceType=row["spaceType"],
        departmentId=row["departmentId"],
        path=row["path"],
        name=row["name"],
        downloadCount=row["downloadCount"],
        lastAccessTs=row["lastAccessTs"],
        lastEditUser=row["lastEditUser"],
        lastEditTs=row["lastEditTs"],
    )
    return FileDetailResponse(item=item)


@router.get('/logs', response_model=AuditQueryResponse)
async def query_logs(
    action: Optional[str] = Query(None),
    path_contains: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=2000),
):
    """简单查询最近的审计日志，可按操作类型和路径关键字过滤。"""
    items: List[AuditRecord] = []
    for rec in reversed(list(_iter_raw_records())):
        if action and rec.action != action:
            continue
        if path_contains and path_contains not in rec.path:
            continue
        items.append(rec)
        if len(items) >= limit:
            break
    return AuditQueryResponse(items=list(reversed(items)))


@router.get('/stats', response_model=FileStatResponse)
async def file_stats(
    spaceType: Optional[str] = Query(None),
    departmentId: Optional[str] = Query(None),
    path_contains: Optional[str] = Query(None),
):
    """基于审计日志的简单访问统计：按文件聚合下载次数和最后访问时间。"""
    agg = {}
    for rec in _iter_raw_records():
        if rec.action not in ('download',):
            continue
        if spaceType and rec.spaceType != spaceType:
            continue
        if departmentId is not None and rec.departmentId != departmentId:
            continue
        if path_contains and path_contains not in rec.path:
            continue
        key = (rec.spaceType, rec.departmentId, rec.path)
        stat = agg.get(key)
        if not stat:
            stat = {
                'downloadCount': 0,
                'lastAccess': None,
            }
            agg[key] = stat
        stat['downloadCount'] += 1
        if stat['lastAccess'] is None or rec.ts > stat['lastAccess']:
            stat['lastAccess'] = rec.ts

    items: List[FileStat] = []
    for (space, dept, p), st in agg.items():
        items.append(FileStat(
            path=p,
            spaceType=space,
            departmentId=dept,
            downloadCount=st['downloadCount'],
            lastAccess=st['lastAccess'],
        ))
    return FileStatResponse(items=items)


class ShareAuditBody(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str = ''
    anchorName: Optional[str] = None
    selectedNames: List[str] = []


@router.post('/share')
async def log_share(req: Request, body: ShareAuditBody):
    """记录前端触发的分享行为到 audit.log。

    action 固定为 'share'，便于后续检索统计。
    """
    client_ip = req.client.host if req.client else ''
    rec = AuditRecord(
        ts=time.time(),
        action='share',
        path=(body.path or ''),
        spaceType=body.spaceType,
        departmentId=(body.departmentId or None),
        clientIp=client_ip,
        detail={
            'anchorName': body.anchorName,
            'selectedNames': body.selectedNames,
        },
    )
    append_audit_record(rec)
    return {"ok": True}
