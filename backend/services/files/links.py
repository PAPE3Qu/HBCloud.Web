"""
文件/文件夹快捷链接服务

链接是一种独立的数据类型，存储在目标目录的 .links.json 文件中。
链接项与真实文件/文件夹完全独立，通过 _link_id 唯一标识。
"""
import json
import time
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import HTTPException

from ...config import SpaceType
from .base import resolve_root, ensure_department_read_access, ensure_department_write_access, write_log
from ...routers.audit import log_action

LINKS_FILE_NAME = ".links.json"


def _get_links_file(root: Path, rel_path: str) -> Path:
    """获取目标目录下的 .links.json 文件路径"""
    safe_rel = Path(rel_path or "").as_posix().lstrip("/") if rel_path else ""
    if safe_rel and safe_rel != ".":
        target_dir = root / safe_rel
    else:
        target_dir = root
    return target_dir / LINKS_FILE_NAME


def _read_links(links_file: Path) -> List[Dict[str, Any]]:
    """读取 .links.json 文件"""
    if not links_file.exists():
        return []
    try:
        with links_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


def _write_links(links_file: Path, links: List[Dict[str, Any]]) -> None:
    """写入 .links.json 文件"""
    links_file.parent.mkdir(parents=True, exist_ok=True)
    with links_file.open("w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)


def get_links_for_directory(
    space_type: str,
    department_id: Optional[str],
    path: str,
    current_user: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """获取指定目录下的所有链接项
    
    返回的链接项格式：
    {
        "name": "显示名称",
        "is_dir": True/False,  # 源文件的类型
        "size": 0,
        "modified_time": 创建时间戳,
        "_is_link": True,  # 关键标记：这是链接项
        "_link_id": "uuid",  # 链接唯一ID（用于选中、删除等操作）
        "_link_source": {  # 源文件信息（用于跳转）
            "spaceType": "...",
            "departmentId": "...",
            "path": "...",
            "name": "..."
        }
    }
    """
    root = resolve_root(space_type, department_id, current_user)
    links_file = _get_links_file(root, path)
    links = _read_links(links_file)
    
    result = []
    for link in links:
        item = {
            "name": link.get("display_name", link.get("source_name", "未知")),
            "is_dir": link.get("source_is_dir", False),
            "size": 0,
            "modified_time": link.get("created_at", 0),
            "_is_link": True,
            "_link_id": link.get("id"),
            "_link_source": {
                "spaceType": link.get("source_space_type"),
                "departmentId": link.get("source_department_id"),
                "path": link.get("source_path"),
                "name": link.get("source_name"),
            }
        }
        result.append(item)
    return result


async def create_link(
    source_space_type: str,
    source_department_id: Optional[str],
    source_path: str,
    source_name: str,
    source_is_dir: bool,
    target_space_type: str,
    target_department_id: Optional[str],
    target_path: str,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    """创建快捷链接"""
    # 校验源读权限
    if source_space_type == SpaceType.DEPARTMENT:
        ensure_department_read_access(source_department_id or "", current_user)
    
    # 校验目标写权限
    if target_space_type == SpaceType.DEPARTMENT:
        ensure_department_write_access(target_department_id or "", current_user)
    
    # 验证源文件存在
    source_root = resolve_root(source_space_type, source_department_id, current_user)
    source_rel = Path(source_path or "").as_posix().lstrip("/") if source_path and source_path != "." else ""
    if source_rel:
        source_file = source_root / source_rel / source_name
    else:
        source_file = source_root / source_name
    
    if not source_file.exists():
        raise HTTPException(status_code=404, detail=f"源文件 {source_name} 不存在")
    
    # 获取目标目录的链接文件
    target_root = resolve_root(target_space_type, target_department_id, current_user)
    links_file = _get_links_file(target_root, target_path)
    
    # 读取现有链接
    links = _read_links(links_file)
    
    # 检查是否已存在同名链接（只检查链接，不检查真实文件）
    for existing in links:
        if existing.get("display_name") == source_name:
            raise HTTPException(status_code=400, detail=f"目标位置已存在同名链接 {source_name}")
    
    # 创建新链接
    link_id = uuid.uuid4().hex
    new_link = {
        "id": link_id,
        "display_name": source_name,
        "source_space_type": source_space_type,
        "source_department_id": source_department_id,
        "source_path": source_path if source_path else ".",
        "source_name": source_name,
        "source_is_dir": source_is_dir,
        "created_at": time.time(),
        "created_by": current_user.get("name", ""),
    }
    
    links.append(new_link)
    _write_links(links_file, links)
    
    # 记录日志
    user_name = current_user.get("name", "unknown")
    source_location = f"{source_space_type}/{source_department_id or ''}/{source_path}/{source_name}"
    target_location = f"{target_space_type}/{target_department_id or ''}/{target_path}"
    
    log_action(
        action="link_create",
        path=target_path or ".",
        spaceType=target_space_type,
        departmentId=target_department_id,
        detail={
            "linkId": link_id,
            "sourceName": source_name,
            "sourceSpaceType": source_space_type,
            "sourceDepartmentId": source_department_id,
            "sourcePath": source_path,
            "sourceIsDir": source_is_dir,
            "editor": user_name,
        },
        text_message=f"link_create {source_location} -> {target_location} by {user_name}",
    )
    write_log(f"[LINK] 创建链接: {source_name} ({source_location}) -> {target_location} by {user_name}")
    
    return {"success": True, "link_id": link_id}


async def delete_link(
    space_type: str,
    department_id: Optional[str],
    path: str,
    link_id: str,
    current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """删除指定的链接（只删除链接数据，不影响源文件）"""
    # 校验写权限
    if space_type == SpaceType.DEPARTMENT:
        ensure_department_write_access(department_id or "", current_user)
    
    root = resolve_root(space_type, department_id, current_user)
    links_file = _get_links_file(root, path)
    
    links = _read_links(links_file)
    original_count = len(links)
    
    # 找到要删除的链接信息（用于日志）
    deleted_link = None
    for l in links:
        if l.get("id") == link_id:
            deleted_link = l
            break
    
    links = [l for l in links if l.get("id") != link_id]
    
    if len(links) == original_count:
        raise HTTPException(status_code=404, detail="链接不存在")
    
    if links:
        _write_links(links_file, links)
    else:
        # 如果没有链接了，删除文件
        try:
            links_file.unlink()
        except Exception:
            pass
    
    # 记录日志
    user_name = current_user.get("name", "unknown")
    link_name = deleted_link.get("display_name", "unknown") if deleted_link else "unknown"
    location = f"{space_type}/{department_id or ''}/{path}"
    
    log_action(
        action="link_delete",
        path=path or ".",
        spaceType=space_type,
        departmentId=department_id,
        detail={
            "linkId": link_id,
            "linkName": link_name,
            "editor": user_name,
        },
        text_message=f"link_delete {link_name} from {location} by {user_name}",
    )
    write_log(f"[LINK] 删除链接: {link_name} (id={link_id}) from {location} by {user_name}")
    
    return {"success": True}


async def check_link_source(
    source_space_type: str,
    source_department_id: Optional[str],
    source_path: str,
    source_name: str,
    current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """检查链接源是否存在且可访问"""
    try:
        # 检查读权限
        if source_space_type == SpaceType.DEPARTMENT:
            try:
                ensure_department_read_access(source_department_id or "", current_user)
            except HTTPException:
                return {"exists": False, "accessible": False, "reason": "no_permission"}
        
        # 检查文件是否存在
        root = resolve_root(source_space_type, source_department_id, current_user)
        source_rel = Path(source_path or "").as_posix().lstrip("/") if source_path and source_path != "." else ""
        if source_rel:
            source_file = root / source_rel / source_name
        else:
            source_file = root / source_name
        
        if source_file.exists():
            return {"exists": True, "accessible": True}
        else:
            return {"exists": False, "accessible": True, "reason": "not_found"}
    except Exception as e:
        return {"exists": False, "accessible": False, "reason": str(e)}
