from pathlib import Path
from typing import List, Optional, Dict, Any
import os
import shutil
from datetime import datetime

from fastapi import HTTPException, Request

from ...config import SpaceType
from .base import resolve_root, write_log, ensure_department_write_access
from . import recycle as recycle_svc
from ...routers.audit import append_audit_record, AuditRecord, move_or_rename_meta, touch_edit_meta, log_action


async def create_folder(payload: Dict[str, Any], current_user: dict, client_ip: str = ""):
    """payload 结构与 FolderCreateRequest 相同。"""
    space_type: str = payload.get("spaceType")
    department_id: Optional[str] = payload.get("departmentId")
    # 部门空间写权限检查
    if space_type == SpaceType.DEPARTMENT:
        ensure_department_write_access(department_id or '', current_user)
    path: str = payload.get("path") or ""
    folder_name: str = payload.get("folderName") or ""

    root = resolve_root(space_type, department_id, current_user)
    safe_rel = Path(path).as_posix().lstrip("/")
    # safe 普通用户手机号路径兼容
    if space_type == SpaceType.SAFE and current_user.get("role") != "super":
        phone = (current_user.get("phone") or "").strip()
        if safe_rel == phone:
            safe_rel = ""

    current_dir = root / safe_rel
    try:
        current_dir = current_dir.resolve()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="目录不存在")

    try:
        current_dir.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径")

    if not current_dir.exists() or not current_dir.is_dir():
        raise HTTPException(status_code=404, detail="目录不存在")

    if not folder_name:
        raise HTTPException(status_code=400, detail="文件夹名称不能为空")
    if any(ch in folder_name for ch in "\\/<>|:?*"):
        raise HTTPException(status_code=400, detail="文件夹名称包含非法字符")

    target = current_dir / folder_name
    if target.exists():
        raise HTTPException(status_code=400, detail="同名文件或文件夹已存在")

    os.makedirs(target, exist_ok=True)

    full_rel = f"{safe_rel}/{folder_name}" if safe_rel else folder_name
    try:
        log_action(
            action="mkdir",
            path=full_rel,
            spaceType=space_type,
            departmentId=department_id,
            clientIp=client_ip,
            detail={
                "editor": current_user.get("name"),
            },
            text_message=(
                f"mkdir {space_type} {department_id or ''} {full_rel} by {current_user.get('name')} from {client_ip}"
            ),
        )
    except Exception:
        pass

    return {"success": True}


async def move_items(payload: Dict[str, Any], current_user: dict):
    """payload 结构与 MoveRequest 相同。"""
    items = payload.get("items") or []
    if not items:
        return {"success": True}

    target_space: str = payload.get("targetSpaceType")
    target_dept: Optional[str] = payload.get("targetDepartmentId")
    # 源部门空间写权限检查
    for it in items:
        if it.get('spaceType') == SpaceType.DEPARTMENT:
            ensure_department_write_access(it.get('departmentId') or '', current_user)
    # 目标部门空间写权限检查
    if target_space == SpaceType.DEPARTMENT:
        ensure_department_write_access(target_dept or '', current_user)
    target_path: str = payload.get("targetPath") or ""
    overwrite: bool = bool(payload.get("overwrite"))

    target_root = resolve_root(target_space, target_dept, current_user)
    target_rel = Path(target_path).as_posix().lstrip("/")
    target_dir = (target_root / target_rel).resolve()
    try:
        target_dir.relative_to(target_root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法目标路径")
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="目标目录不存在")

    for it in items:
        space_type = it.get("spaceType")
        dept_id = it.get("departmentId")
        src_path_str = it.get("path") or ""
        name = it.get("name") or ""
        is_dir = bool(it.get("is_dir"))

        src_root = resolve_root(space_type, dept_id, current_user)
        src_rel = Path(src_path_str).as_posix().lstrip("/")
        # safe 普通用户手机号路径兼容：传入 path 为手机号时视为 safe 根
        if space_type == SpaceType.SAFE and current_user.get("role") != "super":
            phone = (current_user.get("phone") or "").strip()
            if src_rel == phone:
                src_rel = ""

        src_path = (src_root / src_rel / name).resolve()
        try:
            src_path.relative_to(src_root.resolve())
        except ValueError:
            continue
        if not src_path.exists():
            continue
        if is_dir and not src_path.is_dir():
            continue
        if not is_dir and not src_path.is_file():
            continue

        dest_path = (target_dir / name).resolve()
        try:
            dest_path.relative_to(target_root.resolve())
        except ValueError:
            continue

        if dest_path.exists():
            if not overwrite:
                continue
            try:
                if dest_path.is_dir():
                    shutil.rmtree(dest_path, ignore_errors=True)
                else:
                    dest_path.unlink(missing_ok=True)
            except Exception:
                continue
        try:
            shutil.move(str(src_path), str(dest_path))
            from ...routers.audit import log_action  # 延迟导入
            log_action(
                action="move",
                path=f"{src_rel}/{name}" if src_rel else name,
                spaceType=space_type,
                departmentId=dept_id,
                clientIp="",
                detail={
                    "targetSpaceType": target_space,
                    "targetDepartmentId": target_dept,
                    "targetPath": target_path,
                    "isDir": is_dir,
                    "editor": current_user.get("name"),
                },
                text_message=(
                    f"move {space_type}->{target_space} {src_rel}/{name} -> {target_path}/{name} "
                    f"by {current_user.get('name')}"
                ),
            )
            move_or_rename_meta(
                space_type,
                dept_id,
                src_rel,
                name,
                target_space,
                target_dept,
                target_path,
                name,
            )
            touch_edit_meta(
                target_space,
                target_dept,
                target_path,
                name,
                current_user.get("name"),
                datetime.now().timestamp(),
            )
        except Exception:
            continue

    return {"success": True}


async def copy_items(payload: Dict[str, Any], current_user: dict, client_ip: str = ""):
    """payload 结构与 CopyRequest 相同。"""
    items = payload.get("items") or []
    if not items:
        return {"success": True}

    target_space: str = payload.get("targetSpaceType")
    target_dept: Optional[str] = payload.get("targetDepartmentId")
    # 目标部门空间写权限检查
    if target_space == SpaceType.DEPARTMENT:
        ensure_department_write_access(target_dept or '', current_user)
    target_path: str = payload.get("targetPath") or ""
    overwrite: bool = bool(payload.get("overwrite"))

    target_root = resolve_root(target_space, target_dept, current_user)
    target_rel = Path(target_path).as_posix().lstrip("/")
    target_dir = (target_root / target_rel).resolve()
    try:
        target_dir.relative_to(target_root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法目标路径")
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="目标目录不存在")

    for it in items:
        space_type = it.get("spaceType")
        dept_id = it.get("departmentId")
        src_path_str = it.get("path") or ""
        name = it.get("name") or ""
        is_dir = bool(it.get("is_dir"))

        src_root = resolve_root(space_type, dept_id, current_user)
        src_rel = Path(src_path_str).as_posix().lstrip("/")
        # safe 普通用户手机号路径兼容：传入 path 为手机号时视为 safe 根
        if space_type == SpaceType.SAFE and current_user.get("role") != "super":
            phone = (current_user.get("phone") or "").strip()
            if src_rel == phone:
                src_rel = ""

        src_path = (src_root / src_rel / name).resolve()
        try:
            src_path.relative_to(src_root.resolve())
        except ValueError:
            continue
        if not src_path.exists():
            continue
        if is_dir and not src_path.is_dir():
            continue
        if not is_dir and not src_path.is_file():
            continue

        dest_path = (target_dir / name).resolve()
        try:
            dest_path.relative_to(target_root.resolve())
        except ValueError:
            continue

        if dest_path.exists():
            if not overwrite:
                continue
            try:
                if dest_path.is_dir():
                    shutil.rmtree(dest_path, ignore_errors=True)
                else:
                    dest_path.unlink(missing_ok=True)
            except Exception:
                continue
        try:
            if is_dir:
                shutil.copytree(src_path, dest_path)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)
            dest_rel = Path(target_path).as_posix().lstrip("/")
            touch_edit_meta(
                target_space,
                target_dept,
                dest_rel,
                name,
                current_user.get("name"),
                datetime.now().timestamp(),
            )
            # 复制成功后记一条审计日志
            full_src = f"{src_rel}/{name}" if src_rel else name
            log_action(
                action="copy",
                path=full_src,
                spaceType=space_type,
                departmentId=dept_id,
                clientIp=client_ip,
                detail={
                    "targetSpaceType": target_space,
                    "targetDepartmentId": target_dept,
                    "targetPath": target_path,
                    "isDir": is_dir,
                    "overwrite": overwrite,
                    "editor": current_user.get("name"),
                },
                text_message=(
                    f"copy {space_type}->{target_space} {full_src} -> {target_path}/{name} "
                    f"by {current_user.get('name')} from {client_ip}"
                ),
            )
        except Exception:
            continue

    return {"success": True}


async def delete_items(request: Request, payload: Dict[str, Any], current_user: dict):
    """payload 结构与 DeleteRequest 相同，软删除到回收站。"""
    items = payload.get("items") or []
    if not items:
        return {"success": True}

    client_ip = request.client.host if request.client else ""
    now = datetime.now().timestamp()

    # 在真正删除前，对所有涉及部门空间的项目做写权限检查
    for item in items:
        if item.get('spaceType') == SpaceType.DEPARTMENT:
            ensure_department_write_access(item.get('departmentId') or '', current_user)

    for item in items:
        space_type = item.get("spaceType")
        dept_id = item.get("departmentId")
        path = item.get("path") or ""
        name = item.get("name") or ""
        is_dir = bool(item.get("is_dir"))

        root = resolve_root(space_type, dept_id, current_user)
        safe_rel = Path(path).as_posix().lstrip("/")

        if space_type == SpaceType.SAFE and current_user.get("role") != "super":
            phone = (current_user.get("phone") or "").strip()
            if safe_rel == phone:
                safe_rel = ""

        src_path = (root / safe_rel / name).resolve()
        try:
            src_path.relative_to(root.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="非法路径")
        if not src_path.exists():
            raise HTTPException(status_code=404, detail=f"目标不存在: {name}")

        extra: Dict[str, Any] = {}
        if space_type == SpaceType.SAFE:
            extra["safePhone"] = (current_user.get("phone") or "").strip()
        recycle_id = recycle_svc.add_to_recycle_for_path(
            scope="file",
            space_type=space_type,
            department_id=dept_id,
            original_path=safe_rel,
            name=name,
            src_path=src_path,
            is_dir=is_dir,
            current_user=current_user,
            reason="normal_delete",
            extra=extra,
        )

        rel = safe_rel
        full = f"{rel}/{name}" if rel else name
        from ...routers.audit import log_action  # 延迟导入
        log_action(
            action="delete",
            path=full,
            spaceType=space_type,
            departmentId=dept_id,
            clientIp=client_ip,
            detail={"isDir": is_dir, "soft": True, "recycleId": recycle_id},
            text_message=(
                "soft_delete %s %s %s recycleId=%s by %s from %s"
                % (space_type, dept_id or "", full, recycle_id, current_user.get("name"), client_ip)
            ),
        )

    return {"success": True}


async def rename_item(request: Request, payload: Dict[str, Any], current_user: dict):
    """payload 结构与 RenameRequest 相同。"""
    space_type: str = payload.get("spaceType")
    department_id: Optional[str] = payload.get("departmentId")
    # 部门空间写权限检查
    if space_type == SpaceType.DEPARTMENT:
        ensure_department_write_access(department_id or '', current_user)
    path: str = payload.get("path") or ""
    old_name: str = payload.get("oldName") or ""
    new_name: str = payload.get("newName") or ""
    is_dir: bool = bool(payload.get("isDir"))

    root = resolve_root(space_type, department_id, current_user)
    safe_rel = Path(path).as_posix().lstrip("/")

    if space_type == SpaceType.SAFE and current_user.get("role") != "super":
        phone = (current_user.get("phone") or "").strip()
        if safe_rel == phone:
            safe_rel = ""

    current_dir = (root / safe_rel).resolve()

    try:
        current_dir.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径")

    if not current_dir.exists() or not current_dir.is_dir():
        raise HTTPException(status_code=404, detail="目录不存在")

    if not new_name:
        raise HTTPException(status_code=400, detail="新名称不能为空")
    if any(ch in new_name for ch in "\\/<>|:?*"):
        raise HTTPException(status_code=400, detail="新名称包含非法字符")

    src = current_dir / old_name
    dest = current_dir / new_name

    if not src.exists():
        raise HTTPException(status_code=404, detail="原文件/文件夹不存在")

    if dest.exists():
        raise HTTPException(status_code=400, detail="目标名称已存在")

    try:
        src.rename(dest)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名失败: {e}")

    client_ip = request.client.host if request.client else ""
    now = datetime.now().timestamp()
    old_full = f"{safe_rel}/{old_name}" if safe_rel else old_name
    new_full = f"{safe_rel}/{new_name}" if safe_rel else new_name
    from ...routers.audit import log_action  # 延迟导入
    log_action(
        action="rename",
        path=old_full,
        spaceType=space_type,
        departmentId=department_id,
        clientIp=client_ip,
        detail={"newPath": new_full, "isDir": is_dir, "editor": current_user.get("name")},
        text_message=(
            f"rename {space_type} {department_id or ''} {old_full} -> {new_full} "
            f"by {current_user.get('name')} from {client_ip}"
        ),
    )
    move_or_rename_meta(
        space_type,
        department_id,
        safe_rel,
        old_name,
        space_type,
        department_id,
        safe_rel,
        new_name,
    )
    touch_edit_meta(space_type, department_id, safe_rel, new_name, current_user.get("name"), now)

    return {"success": True}