from pathlib import Path
from typing import List, Optional, Dict, Any
import os

from fastapi import HTTPException

from ...config import SpaceType
from .base import resolve_root, ensure_department_read_access
from . import dept as dept_svc
from . import dept_roles as dept_roles_svc
from ...routers.audit import log_action


async def list_files(spaceType: str, departmentId: Optional[str], path: str, current_user: Dict[str, Any], client_ip: str = "") -> Dict[str, Any]:
    # 部门空间：在解析根目录前统一做空间开放与角色校验
    if spaceType == SpaceType.DEPARTMENT:
        dept_id = (departmentId or '').strip()
        ensure_department_read_access(dept_id, current_user)

    root = resolve_root(spaceType, departmentId, current_user)
    raw_path = path or ""
    if raw_path in ("", ".", "./"):
        logical_rel = "."
        safe_rel = ""
    else:
        logical_rel = raw_path
        safe_rel = Path(raw_path).as_posix().lstrip("/")

    if spaceType == SpaceType.SAFE and current_user.get("role") != "super":
        phone = (current_user.get("phone") or "").strip()
        if safe_rel == phone:
            logical_rel = "."
            safe_rel = ""

    current_dir = root / safe_rel
    if not current_dir.exists():
        if (spaceType == SpaceType.SAFE and not safe_rel) or (spaceType == SpaceType.DEPARTMENT and not safe_rel):
            current_dir.mkdir(parents=True, exist_ok=True)
            return {"current_path": logical_rel, "items": []}
        raise HTTPException(status_code=404, detail="目录不存在")
    try:
        current_dir = current_dir.resolve()
        current_dir.relative_to(root.resolve())
    except Exception:
        raise HTTPException(status_code=400, detail="非法路径")
    if not current_dir.is_dir():
        raise HTTPException(status_code=404, detail="目录不存在")

    items: List[Dict[str, Any]] = []
    for entry in current_dir.iterdir():
        if spaceType == SpaceType.PUBLIC and entry.is_dir() and entry.name == "__packs__":
            continue
        if entry.name == "config.json" and spaceType == SpaceType.DEPARTMENT:
            continue
        stat = entry.stat()
        items.append(
            {
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": 0 if entry.is_dir() else stat.st_size,
                "modified_time": stat.st_mtime,
            }
        )
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    result = {"current_path": logical_rel, "items": items}
    try:
        log_action(
            action="list",
            path=logical_rel,
            spaceType=spaceType,
            departmentId=departmentId,
            clientIp=client_ip,
            detail={
                "itemCount": len(items),
                "editor": current_user.get("name"),
            },
            text_message=(
                f"list {spaceType} {departmentId or ''} {logical_rel} items={len(items)} by {current_user.get('name')} from {client_ip}"
            ),
        )
    except Exception:
        pass
    return result


async def get_directory_size(spaceType: str, departmentId: Optional[str], path: str, name: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
    """计算指定目录的总大小（包含子目录中的所有文件）"""
    # 部门空间：校验读权限
    if spaceType == SpaceType.DEPARTMENT:
        dept_id = (departmentId or '').strip()
        ensure_department_read_access(dept_id, current_user)

    root = resolve_root(spaceType, departmentId, current_user)
    
    # 处理路径：确保safe_rel不包含前导/
    safe_rel = Path(path or "").as_posix().lstrip("/") if path else ""
    
    # 构建目标目录路径
    if safe_rel:
        target_dir = (root / safe_rel / name).resolve()
    else:
        target_dir = (root / name).resolve()
    
    # 验证路径安全性
    try:
        target_dir.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径")
    
    if not target_dir.exists():
        raise HTTPException(status_code=404, detail="目录不存在")
    
    if not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="不是目录")
    
    # 递归计算目录大小
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(target_dir):
            for fname in filenames:
                fpath = Path(dirpath) / fname
                try:
                    total_size += fpath.stat().st_size
                except OSError:
                    pass
    except Exception:
        pass
    
    return {"size": total_size}
