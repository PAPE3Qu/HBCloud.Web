import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import HTTPException

from ...config import DATA_ROOT, DEPT_ROOT, SpaceType
from ..files.base import write_log, resolve_root, ensure_department_read_access, ensure_department_write_access
from ...routers.audit import append_audit_record, AuditRecord, touch_edit_meta, delete_meta

RECYCLE_DB_PATH = DATA_ROOT / "recycle_bin.db"
RECYCLE_ROOT = DATA_ROOT / "recycle"
RECYCLE_COMMON_ROOT = RECYCLE_ROOT / "common"
RECYCLE_SAFE_ROOT = RECYCLE_ROOT / "safe-r"
RECYCLE_DEPT_ROOT = RECYCLE_ROOT / "dept"
for _p in (RECYCLE_ROOT, RECYCLE_COMMON_ROOT, RECYCLE_SAFE_ROOT, RECYCLE_DEPT_ROOT):
    _p.mkdir(parents=True, exist_ok=True)


def get_recycle_conn() -> sqlite3.Connection:
    need_init = not RECYCLE_DB_PATH.exists()
    conn = sqlite3.connect(str(RECYCLE_DB_PATH))
    if need_init:
        _init_recycle_db(conn)
    conn.row_factory = sqlite3.Row
    return conn


def _init_recycle_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS recycle_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT NOT NULL,
            space_type TEXT NOT NULL,
            department_id TEXT,
            original_path TEXT NOT NULL,
            name TEXT NOT NULL,
            is_dir INTEGER NOT NULL,
            deleted_at REAL NOT NULL,
            deleted_by TEXT,
            deleted_by_id TEXT,
            reason TEXT,
            storage_path TEXT NOT NULL,
            extra TEXT
        );
        """
    )
    conn.commit()


def insert_recycle_record(
    scope: str,
    space_type: str,
    department_id: Optional[str],
    original_path: str,
    name: str,
    is_dir: bool,
    deleted_by: Optional[str],
    deleted_by_id: Optional[str],
    reason: str,
    storage_path: str,
    extra: Optional[Dict[str, Any]] = None,
) -> int:
    conn = get_recycle_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO recycle_items
            (scope, space_type, department_id, original_path, name, is_dir,
             deleted_at, deleted_by, deleted_by_id, reason, storage_path, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scope,
                space_type,
                department_id,
                original_path,
                name,
                1 if is_dir else 0,
                datetime.utcnow().timestamp(),
                deleted_by,
                deleted_by_id,
                reason,
                storage_path,
                json.dumps(extra or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def fetch_recycle_rows_by_ids(ids: List[int]) -> List[sqlite3.Row]:
    if not ids:
        return []
    conn = get_recycle_conn()
    try:
        placeholders = ",".join(["?"] * len(ids))
        sql = "SELECT * FROM recycle_items WHERE id IN (" + placeholders + ")"
        cur = conn.cursor()
        cur.execute(sql, ids)
        rows = cur.fetchall()
        return list(rows)
    finally:
        conn.close()


def delete_recycle_rows(ids: List[int]) -> None:
    if not ids:
        return
    conn = get_recycle_conn()
    try:
        placeholders = ",".join(["?"] * len(ids))
        sql = "DELETE FROM recycle_items WHERE id IN (" + placeholders + ")"
        cur = conn.cursor()
        cur.execute(sql, ids)
        conn.commit()
    finally:
        conn.close()


def auto_rename(dest: Path) -> Path:
    parent = dest.parent
    stem = dest.stem
    suffix = dest.suffix
    cand = parent / (stem + "(恢复)" + suffix)
    if not cand.exists():
        return cand
    index = 1
    while True:
        cand = parent / ("%s(恢复-%d)%s" % (stem, index, suffix))
        if not cand.exists():
            return cand
        index += 1


def auto_rename_for_dept(base_dir: Path, original_name: str) -> Path:
    """根据原始部门显示名生成还原目录名。

    规则：
    - 若 base_dir/original_name 不存在：直接使用 original_name
    - 若已存在同名目录：依次使用 original_name(恢复)、original_name(恢复-2)、...
    """
    # 优先：不冲突则直接用原名
    direct = base_dir / f"{original_name}"
    if not direct.exists():
        return direct

    # 冲突：第一候选为(恢复)
    candidate = base_dir / f"{original_name}(恢复)"
    if not candidate.exists():
        return candidate

    # 从(恢复-2)开始累加
    index = 2
    while True:
        candidate = base_dir / f"{original_name}(恢复-{index})"
        if not candidate.exists():
            return candidate
        index += 1


def get_recycle_bucket_base(scope: str, space_type: str, current_user: Dict[str, Any], department_id: Optional[str]) -> Path:
    if scope == "department":
        base_dir = RECYCLE_DEPT_ROOT
    elif space_type == SpaceType.SAFE:
        phone = (current_user.get("phone") or "").strip()
        if not phone:
            raise HTTPException(status_code=400, detail="当前用户缺少手机号信息，无法回收个人保险库文件")
        base_dir = RECYCLE_SAFE_ROOT / phone
    else:
        base_dir = RECYCLE_COMMON_ROOT
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def add_to_recycle_for_path(
    scope: str,
    space_type: str,
    department_id: Optional[str],
    original_path: str,
    name: str,
    src_path: Path,
    is_dir: bool,
    current_user: Dict[str, Any],
    reason: str,
    extra: Optional[Dict[str, Any]] = None,
) -> int:
    deleted_by = current_user.get("name") or current_user.get("phone") or None
    deleted_by_id = current_user.get("id") or None

    tmp_storage_path = "recycle/tmp/" + name
    recycle_id = insert_recycle_record(
        scope=scope,
        space_type=space_type,
        department_id=department_id,
        original_path=original_path,
        name=name,
        is_dir=is_dir,
        deleted_by=deleted_by,
        deleted_by_id=deleted_by_id,
        reason=reason,
        storage_path=tmp_storage_path,
        extra=extra,
    )

    bucket_base = get_recycle_bucket_base(scope, space_type, current_user, department_id)
    ym = datetime.utcnow().strftime("%Y%m")
    target_root = bucket_base / ym / str(recycle_id)
    target_root.mkdir(parents=True, exist_ok=True)
    target_path = target_root / name

    try:
        shutil.move(str(src_path), str(target_path))
    except Exception as e:
        delete_recycle_rows([recycle_id])
        raise HTTPException(status_code=500, detail="移动到回收站失败: %s" % e)

    conn = get_recycle_conn()
    try:
        cur = conn.cursor()
        rel_storage = target_path.relative_to(DATA_ROOT).as_posix()
        cur.execute("UPDATE recycle_items SET storage_path=? WHERE id=?", (rel_storage, recycle_id))
        conn.commit()
    finally:
        conn.close()

    return recycle_id


def build_recycle_item_from_row(row: sqlite3.Row) -> Dict[str, Any]:
    try:
        extra = json.loads(row["extra"] or "{}")
    except Exception:
        extra = {}
    return {
        "id": int(row["id"]),
        "scope": row["scope"],
        "spaceType": row["space_type"],
        "departmentId": row["department_id"],
        "originalPath": row["original_path"],
        "name": row["name"],
        "isDir": bool(row["is_dir"]),
        "deletedAt": float(row["deleted_at"]),
        "deletedBy": row["deleted_by"],
        "extra": extra,
    }


def ensure_can_access_recycle_row(row: sqlite3.Row, current_user: Dict[str, Any]) -> bool:
    if current_user.get("role") == "super":
        return True
    space_type = row["space_type"]
    if space_type == SpaceType.SAFE:
        try:
            extra = json.loads(row["extra"] or "{}")
        except Exception:
            extra = {}
        safe_phone = extra.get("safePhone") or extra.get("phone")
        cur_phone = (current_user.get("phone") or "").strip()
        return bool(safe_phone and cur_phone and safe_phone == cur_phone)
    return True


def restore_single(row: sqlite3.Row, current_user: Dict[str, Any]) -> Optional[str]:
    if not ensure_can_access_recycle_row(row, current_user):
        raise HTTPException(status_code=403, detail="无权还原该回收项")

    space_type = row["space_type"]
    department_id = row["department_id"]
    original_path = row["original_path"] or ""
    name = row["name"]
    is_dir = bool(row["is_dir"])
    storage_path = row["storage_path"] or ""
    scope = row["scope"]

    src = (DATA_ROOT / storage_path).resolve()
    if not src.exists():
        delete_recycle_rows([int(row["id"])])
        return None

    if scope == "department":
        ensure_department_write_access(department_id or '', current_user)
        # 部门还原：按照“原name(恢复)/(恢复-2)/(恢复-3)”命名
        # 优先从extra中拿原始显示名，其次尝试读取当前回收目录下的config.json
        try:
            extra = json.loads(row["extra"] or "{}")
        except Exception:
            extra = {}

        original_display_name = extra.get("name") or extra.get("deptName") or extra.get("departmentName")

        # 如果extra里没有，则尝试读取回收站目录里的config.json（如果有）
        if not original_display_name and src.is_dir():
            cfg_path_in_recycle = src / "config.json"
            if cfg_path_in_recycle.exists():
                try:
                    cfg_in_recycle = json.loads(cfg_path_in_recycle.read_text(encoding="utf-8"))
                    original_display_name = cfg_in_recycle.get("name")
                except Exception:
                    original_display_name = None

        # 兜底：用当前目录名
        if not original_display_name:
            original_display_name = src.name

        root = DEPT_ROOT
        dest_dir = root
        # 根据原始显示名生成最终目录名
        final_dest = auto_rename_for_dept(dest_dir, original_display_name)

        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            final_dest = final_dest.resolve()
            final_dest.relative_to(root.resolve())
        except Exception:
            raise HTTPException(status_code=400, detail="非法还原目标路径")

        try:
            shutil.move(str(src), str(final_dest))
        except Exception as e:
            raise HTTPException(status_code=500, detail="还原失败: %s" % e)

        # 删除 DB 记录
        delete_recycle_rows([int(row["id"])])

        # 同步更新 config.json
        cfg_path = final_dest / "config.json"
        try:
            if cfg_path.exists():
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            else:
                cfg = {}
        except Exception:
            cfg = {}

        cfg_name = final_dest.name
        cfg["id"] = final_dest.name
        cfg["name"] = cfg_name
        try:
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            # 配置写入失败不影响主流程
            pass

        dept_id_restored = final_dest.name
        from ...routers.audit import log_action  # 延迟导入
        log_action(
            action="restore",
            path=dept_id_restored,
            spaceType=SpaceType.DEPARTMENT,
            departmentId=dept_id_restored,
            clientIp="",
            detail={"scope": "department"},
            text_message=(
                "restore department %s from recycle #%s" % (dept_id_restored, row["id"])
            ),
        )
        return dept_id_restored

    root = resolve_root(space_type, department_id, current_user)
    rel = original_path.lstrip("/") if original_path else ""
    dest_dir = (root / rel) if rel else root
    dest = dest_dir / name

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest.resolve()
    try:
        dest.relative_to(root.resolve())
    except Exception:
        raise HTTPException(status_code=400, detail="非法还原目标路径")

    final_dest = dest
    if final_dest.exists():
        final_dest = auto_rename(final_dest)

    try:
        shutil.move(str(src), str(final_dest))
    except Exception as e:
        raise HTTPException(status_code=500, detail="还原失败: %s" % e)

    delete_recycle_rows([int(row["id"])])

    final_rel = final_dest.relative_to(root).parent.as_posix()
    final_name = final_dest.name
    if not is_dir:
        touch_edit_meta(space_type, department_id, final_rel, final_name, current_user.get("name"), datetime.now().timestamp())

    from ...routers.audit import log_action  # 延迟导入
    log_action(
        action="restore",
        path=("%s/%s" % (original_path, name)) if original_path else name,
        spaceType=space_type,
        departmentId=department_id,
        clientIp="",
        detail={"newPath": (final_rel + "/" + final_name) if final_rel else final_name},
        text_message=(
            "restore %s %s %s/%s -> %s/%s"
            % (space_type, department_id or "", original_path, name, final_rel, final_name)
        ),
    )
    return final_rel


def purge_single(row: sqlite3.Row, current_user: Dict[str, Any]) -> None:
    if not ensure_can_access_recycle_row(row, current_user):
        raise HTTPException(status_code=403, detail="无权彻底删除该回收项")

    space_type = row["space_type"]
    department_id = row["department_id"]
    original_path = row["original_path"] or ""
    name = row["name"]
    is_dir = bool(row["is_dir"])
    storage_path = row["storage_path"] or ""
    scope = row["scope"]

    src = (DATA_ROOT / storage_path).resolve()
    if src.exists():
        try:
            if src.is_dir():
                shutil.rmtree(src, ignore_errors=True)
            else:
                src.unlink()
        except Exception:
            pass

    delete_recycle_rows([int(row["id"])])

    if scope != "department" and not is_dir:
        delete_meta(space_type, department_id, original_path.lstrip("/"), name)

    from ...routers.audit import log_action  # 延迟导入
    log_action(
        action="purge",
        path=("%s/%s" % (original_path, name)) if original_path else name,
        spaceType=space_type,
        departmentId=department_id,
        clientIp="",
        detail={"scope": scope, "isDir": is_dir},
        text_message=(
            "purge %s %s %s/%s from recycle #%s"
            % (space_type, department_id or "", original_path, name, row["id"])
        ),
    )


# -------- service接口，供router调用 --------

async def list_recycle_items(scope: Optional[str], spaceType: Optional[str], keyword: Optional[str], page: int, pageSize: int, current_user: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_recycle_conn()
    try:
        cur = conn.cursor()
        where = []
        params: List[Any] = []
        if scope and scope != "all":
            where.append("scope = ?")
            params.append(scope)
        if spaceType:
            where.append("space_type = ?")
            params.append(spaceType)
        if keyword:
            like = "%%" + keyword + "%%"
            where.append("(name LIKE ? OR original_path LIKE ?)")
            params.append(like)
            params.append(like)
        sql_base = "SELECT * FROM recycle_items"
        if where:
            sql_base += " WHERE " + " AND ".join(where)
        sql_count = "SELECT COUNT(1) FROM (" + sql_base + ") t"
        cur.execute(sql_count, params)
        total_row = cur.fetchone()
        total = int(total_row[0]) if total_row else 0

        offset = (page - 1) * pageSize
        sql_page = sql_base + " ORDER BY deleted_at DESC LIMIT ? OFFSET ?"
        page_params = list(params)
        page_params.append(pageSize)
        page_params.append(offset)
        cur.execute(sql_page, page_params)
        rows = cur.fetchall()

        items: List[Dict[str, Any]] = []
        for row in rows:
            if not ensure_can_access_recycle_row(row, current_user):
                continue

            # 关键：部门本体的回收记录（scope=department）不应再做部门目录访问校验。
            # 因为删除部门后 DEPT_ROOT/dept_id 已不存在，任何“读部门空间”校验都会失败，
            # 导致回收站列表把部门条目过滤掉（包括 super）。
            # 这里仅对“部门空间里的文件/文件夹”（space_type=department 且 scope!=department）保留 acl 过滤。
            if row["space_type"] == SpaceType.DEPARTMENT and row["scope"] != "department":
                dept_id = (row["department_id"] or '').strip()
                if dept_id:
                    try:
                        ensure_department_read_access(dept_id, current_user)
                    except HTTPException:
                        continue
                else:
                    write_log(f"recycle_list_skip_dept_acl_missing_dept_id rid={row['id']} by={current_user.get('name') or current_user.get('phone')}")

            items.append(build_recycle_item_from_row(row))

        return {"items": items, "total": total}
    finally:
        conn.close()


async def restore_recycle_items(payload: Dict[str, Any], current_user: Dict[str, Any]) -> Dict[str, Any]:
    ids = payload.get("ids") or []
    if not ids:
        return {"success": True, "restored": [], "failed": []}

    rows = fetch_recycle_rows_by_ids([int(i) for i in ids])
    by_id = {int(r["id"]): r for r in rows}

    restored: List[int] = []
    failed: List[Dict[str, Any]] = []

    for rid in ids:
        row = by_id.get(int(rid))
        if row is None:
            failed.append({"id": rid, "reason": "not_found"})
            continue

        # 逐条校验 scope/space 的访问与操作权限：无权则记录失败，不中断
        if not ensure_can_access_recycle_row(row, current_user):
            failed.append({"id": rid, "reason": "无权操作该回收项"})
            continue

        try:
            # 部门空间：需要写权限（dept/member/super/op）
            if row["space_type"] == SpaceType.DEPARTMENT:
                dept_id = (row["department_id"] or '').strip()
                if not dept_id:
                    failed.append({"id": rid, "reason": "回收记录缺少 departmentId"})
                    continue
                ensure_department_write_access(dept_id, current_user)

            restore_single(row, current_user)
            restored.append(rid)
        except HTTPException as he:
            failed.append({"id": rid, "reason": he.detail})
        except Exception as e:
            failed.append({"id": rid, "reason": str(e)})

    return {"success": True, "restored": restored, "failed": failed}


async def purge_recycle_items(payload: Dict[str, Any], current_user: Dict[str, Any]) -> Dict[str, Any]:
    ids = payload.get("ids") or []
    if not ids:
        return {"success": True, "purged": [], "failed": []}

    rows = fetch_recycle_rows_by_ids([int(i) for i in ids])
    by_id = {int(r["id"]): r for r in rows}

    purged: List[int] = []
    failed: List[Dict[str, Any]] = []

    for rid in ids:
        row = by_id.get(int(rid))
        if row is None:
            failed.append({"id": rid, "reason": "not_found"})
            continue

        if not ensure_can_access_recycle_row(row, current_user):
            failed.append({"id": rid, "reason": "无权操作该回收项"})
            continue

        try:
            if row["space_type"] == SpaceType.DEPARTMENT:
                dept_id = (row["department_id"] or '').strip()
                if not dept_id:
                    failed.append({"id": rid, "reason": "回收记录缺少 departmentId"})
                    continue
                ensure_department_write_access(dept_id, current_user)

            purge_single(row, current_user)
            purged.append(rid)
        except HTTPException as he:
            failed.append({"id": rid, "reason": he.detail})
        except Exception as e:
            failed.append({"id": rid, "reason": str(e)})

    return {"success": True, "purged": purged, "failed": failed}


async def empty_recycle(current_user: Dict[str, Any]) -> Dict[str, Any]:
    if current_user.get("role") != "super":
        raise HTTPException(status_code=403, detail="仅超级管理员可清空回收站")
    conn = get_recycle_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM recycle_items")
        rows = cur.fetchall()
    finally:
        conn.close()
    for row in rows:
        if row["space_type"] == SpaceType.DEPARTMENT:
            ensure_department_write_access(row["department_id"] or '', current_user)
        purge_single(row, current_user)
    return {"success": True}
