import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ...config import DEPT_ROOT, SpaceType
from .base import write_log
from ..files import recycle as recycle_svc


def _read_dept_config(dept_dir: Path) -> dict:
    cfg_path = dept_dir / "config.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_dept_config(dept_dir: Path, data: dict) -> None:
    cfg_path = dept_dir / "config.json"
    cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_spaces() -> List[str]:
    return [SpaceType.PUBLIC, SpaceType.DEPARTMENT]


def list_departments() -> List[Dict[str, Any]]:
    if not DEPT_ROOT.exists():
        return []
    result: List[Dict[str, Any]] = []
    for item in DEPT_ROOT.iterdir():
        if item.is_dir():
            cfg = _read_dept_config(item)
            name = cfg.get("name") or item.name
            result.append({"id": item.name, "name": name})
    return result


def create_department(payload, current_user: dict) -> Dict[str, Any]:
    from ...routers.files import CreateDeptRequest  # type: ignore
    if not payload.id or any(ch in payload.id for ch in "\\/<>|:?*"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="部门 ID 非法")
    if not payload.deletePassword or len(payload.deletePassword.strip()) != 6:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="部门删除密码必须为 6 位")

    dept_dir = DEPT_ROOT / payload.id
    if dept_dir.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="部门已存在")

    os.makedirs(dept_dir, exist_ok=True)

    from ...routers.auth import pwd_context
    cfg = {
        "id": payload.id,
        "name": payload.name or payload.id,
        "creator": {
            "id": current_user.get("id"),
            "phone": current_user.get("phone"),
            "name": current_user.get("name"),
        },
        "deletePasswordHash": pwd_context.hash(payload.deletePassword.strip()),
        # 默认：新建部门空间为开放状态
        "isOpen": True,
    }
    _write_dept_config(dept_dir, cfg)
    return {"id": payload.id, "name": cfg["name"]}


def delete_department(payload, current_user: dict) -> Dict[str, Any]:
    from fastapi import HTTPException
    dept_dir = DEPT_ROOT / payload.id
    if not dept_dir.exists() or not dept_dir.is_dir():
        raise HTTPException(status_code=404, detail="部门不存在")

    if current_user.get("role") != "super":
        cfg = _read_dept_config(dept_dir)
        pwd_hash = cfg.get("deletePasswordHash") or ""
        if not pwd_hash:
            raise HTTPException(status_code=400, detail="该部门未设置删除密码，禁止删除")
        raw_pwd = (payload.deletePassword or "").strip()
        from ...routers.auth import pwd_context
        if len(raw_pwd) != 6 or not pwd_context.verify(raw_pwd, pwd_hash):
            raise HTTPException(status_code=403, detail="部门删除密码错误")

    if not dept_dir.exists() or not dept_dir.is_dir():
        raise HTTPException(status_code=404, detail="部门不存在")

    # ===== 联动清理：部门角色配置、部门文件索引 =====
    try:
        from . import dept_roles as dept_roles_svc
        removed_roles = dept_roles_svc.delete_dept_roles(payload.id)
    except Exception as e:
        removed_roles = 0
        write_log(f"delete_department_cleanup_dept_roles_failed dept={payload.id} err={e}")

    try:
        from ...routers.audit import delete_meta_by_department
        removed_meta = delete_meta_by_department(SpaceType.DEPARTMENT, payload.id)
    except Exception as e:
        removed_meta = 0
        write_log(f"delete_department_cleanup_file_detail_failed dept={payload.id} err={e}")

    # ===== 联动清理：回收站 DB 中与该部门相关的历史记录（不可逆口径） =====
    removed_recycle_rows = 0
    try:
        from . import recycle as recycle_svc
        # 仅删除“部门空间”相关记录：
        # - 部门本体：scope=department 且 department_id=deptId
        # - 部门内文件/文件夹：space_type=department 且 department_id=deptId
        conn = recycle_svc.get_recycle_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM recycle_items
                WHERE department_id = ?
                  AND (space_type = 'department' OR scope = 'department')
                """,
                (payload.id,),
            )
            removed_recycle_rows = int(cur.rowcount or 0)
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        removed_recycle_rows = 0
        write_log(f"delete_department_cleanup_recycle_db_failed dept={payload.id} err={e}")

    recycle_id = recycle_svc.add_to_recycle_for_path(
        scope="department",
        space_type=SpaceType.DEPARTMENT,
        department_id=payload.id,
        original_path="",
        name=payload.id,
        src_path=dept_dir,
        is_dir=True,
        current_user=current_user,
        reason="dept_delete",
        extra={
            "deptId": payload.id,
            "removedDeptRoles": removed_roles,
            "removedFileMeta": removed_meta,
            "removedRecycleRows": removed_recycle_rows,
        },
    )

    from ...routers.audit import append_audit_record, AuditRecord
    append_audit_record(
        AuditRecord(
            ts=datetime.now().timestamp(),
            action="delete",
            path=payload.id,
            spaceType=SpaceType.DEPARTMENT,
            departmentId=payload.id,
            clientIp="",
            detail={
                "scope": "department",
                "soft": True,
                "recycleId": recycle_id,
                "removedDeptRoles": removed_roles,
                "removedFileMeta": removed_meta,
                "removedRecycleRows": removed_recycle_rows,
            },
        )
    )
    write_log("soft_delete_department %s recycleId=%s by %s" % (payload.id, recycle_id, current_user.get("name")))
    return {
        "success": True,
        "recycleId": recycle_id,
        "removedDeptRoles": removed_roles,
        "removedFileMeta": removed_meta,
        "removedRecycleRows": removed_recycle_rows,
    }


def get_department_config(dept_id: str) -> Dict[str, Any]:
    """返回单个部门的完整配置信息（去除敏感字段）。"""
    dept_dir = DEPT_ROOT / dept_id
    if not dept_dir.exists() or not dept_dir.is_dir():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="部门不存在")

    cfg = _read_dept_config(dept_dir) or {}
    # 删除敏感字段，仅返回是否设置了密码
    delete_hash = cfg.pop("deletePasswordHash", None)
    cfg["deletePasswordProtected"] = bool(delete_hash)
    # 确保 id/name 存在
    cfg.setdefault("id", dept_id)
    cfg.setdefault("name", dept_id)
    # 确保 isOpen 字段存在：老数据默认视为已开放
    if "isOpen" not in cfg:
        cfg["isOpen"] = True
    return cfg
