from pathlib import Path
from typing import List, Optional, Dict, Any
import os
import zipfile
from datetime import datetime

from fastapi import HTTPException, Request

from ...config import SpaceType
from .base import resolve_root, write_log, ensure_department_read_access, ensure_department_write_access
from ...routers.audit import append_audit_record, AuditRecord, log_action


async def search_items(spaceType: str, departmentId: Optional[str], path: str, keyword: str, current_user: Dict[str, Any], client_ip: str = "") -> List[Dict[str, Any]]:
    """对应 legacy /search，返回由 SearchItem 字段组成的 dict 列表。"""
    # 部门空间搜索前做读权限检查
    if spaceType == SpaceType.DEPARTMENT:
        ensure_department_read_access(departmentId or '', current_user)

    root = resolve_root(spaceType, departmentId, current_user)
    safe_rel = Path(path).as_posix().lstrip("/")
    start_dir = (root / safe_rel).resolve()

    try:
        start_dir.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径")

    if not start_dir.exists() or not start_dir.is_dir():
        raise HTTPException(status_code=404, detail="起始目录不存在")

    keyword_lower = (keyword or "").lower()
    results: List[Dict[str, Any]] = []

    for dirpath, dirnames, filenames in os.walk(start_dir):
        base = Path(dirpath)
        if spaceType == SpaceType.DEPARTMENT and base.name == "" and "config.json" in filenames:
            filenames = [f for f in filenames if f != "config.json"]

        for d in dirnames:
            if not keyword_lower or keyword_lower in d.lower():
                full_d = base / d
                stat = full_d.stat()
                rel_path = full_d.relative_to(root).parent.as_posix()
                results.append({
                    "name": d,
                    "is_dir": True,
                    "size": 0,
                    "modified_time": stat.st_mtime,
                    "path": rel_path,
                })

        for f in filenames:
            if not keyword_lower or keyword_lower in f.lower():
                full_f = base / f
                stat = full_f.stat()
                rel_path = full_f.relative_to(root).parent.as_posix()
                results.append({
                    "name": f,
                    "is_dir": False,
                    "size": stat.st_size,
                    "modified_time": stat.st_mtime,
                    "path": rel_path,
                })

    try:
        log_action(
            action="search",
            path=safe_rel or "./",
            spaceType=spaceType,
            departmentId=departmentId,
            clientIp=client_ip,
            detail={
                "keyword": keyword or "",
                "resultCount": len(results),
                "editor": current_user.get("name"),
            },
            text_message=(
                f"search {spaceType} {departmentId or ''} {safe_rel or './'} keyword='{keyword or ''}' results={len(results)} by {current_user.get('name')} from {client_ip}"
            ),
        )
    except Exception:
        # 审计失败不影响搜索结果
        pass

    return results


async def unzip_file(payload: Dict[str, Any], current_user: dict, client_ip: str = ""):
    """在指定空间和路径下，对选中的 ZIP 文件进行解压缩。payload 结构与 UnzipRequest 相同。"""
    space_type: str = payload.get("spaceType")
    department_id: Optional[str] = payload.get("departmentId")
    path: str = payload.get("path") or ""
    name: str = payload.get("name") or ""
    overwrite: bool = bool(payload.get("overwrite"))

    # 部门空间解压前做写权限检查
    if space_type == SpaceType.DEPARTMENT:
        ensure_department_write_access(department_id or '', current_user)

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

    zip_path = (current_dir / name).resolve()
    try:
        zip_path.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径")
    if not zip_path.exists() or not zip_path.is_file():
        raise HTTPException(status_code=404, detail="ZIP 文件不存在")

    if not zip_path.name.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持解压 .zip 文件")

    extracted_count = 0
    skipped_existing = 0
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                member_path = Path(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    continue
                target = (current_dir / member_path).resolve()
                try:
                    target.relative_to(root.resolve())
                except ValueError:
                    continue
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if target.exists() and not overwrite:
                    skipped_existing += 1
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member, "r") as src, open(target, "wb") as dst:
                    import shutil as _shutil
                    _shutil.copyfileobj(src, dst)
                extracted_count += 1
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="无效的 ZIP 文件")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解压失败: {e}")

    try:
        log_action(
            action="unzip",
            path=f"{safe_rel}/{name}" if safe_rel else name,
            spaceType=space_type,
            departmentId=department_id,
            clientIp=client_ip,
            detail={
                "overwrite": overwrite,
                "extracted": extracted_count,
                "skippedExisting": skipped_existing,
                "editor": current_user.get("name"),
            },
            text_message=(
                f"unzip {space_type} {department_id or ''} {safe_rel or './'}/{name} overwrite={overwrite} "
                f"extracted={extracted_count} skipped={skipped_existing} by {current_user.get('name')} from {client_ip}"
            ),
        )
    except Exception:
        pass

    return {"success": True}


async def compress_items(payload: Dict[str, Any], current_user: dict, client_ip: str = ""):
    """在当前目录下将选中的文件/文件夹压缩为 zip 文件。payload 结构与 CompressRequest 相同。"""
    items = payload.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="未选择任何项")

    zip_name_raw: str = payload.get("zipName") or ""
    if not zip_name_raw:
        raise HTTPException(status_code=400, detail="压缩文件名不能为空")

    space_type: str = payload.get("spaceType")
    department_id: Optional[str] = payload.get("departmentId")
    path: str = payload.get("path") or ""

    # 部门空间压缩前做写权限检查
    if space_type == SpaceType.DEPARTMENT:
        ensure_department_write_access(department_id or '', current_user)

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

    zip_name = zip_name_raw if zip_name_raw.lower().endswith(".zip") else zip_name_raw + ".zip"
    zip_path = (current_dir / zip_name).resolve()
    try:
        zip_path.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径")

    if zip_path.exists():
        if zip_path.is_dir():
            raise HTTPException(status_code=400, detail="存在同名目录，无法创建 Zip 文件")
        zip_path.unlink(missing_ok=True)

    try:
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for it in items:
                name = it.get("name") or ""
                is_dir = bool(it.get("is_dir"))
                src = (current_dir / name).resolve()
                try:
                    src.relative_to(root.resolve())
                except ValueError:
                    continue
                if not src.exists():
                    continue
                if is_dir and not src.is_dir():
                    continue
                if not is_dir and not src.is_file():
                    continue
                if src.is_dir():
                    for dirpath, dirnames, filenames in os.walk(src):
                        base = Path(dirpath)
                        for fname in filenames:
                            full = base / fname
                            rel = full.relative_to(current_dir).as_posix()
                            zf.write(full, rel)
                else:
                    rel = src.relative_to(current_dir).as_posix()
                    zf.write(src, rel)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"压缩失败: {e}")

    write_log(
        f"compress {space_type} {department_id or ''} {safe_rel} -> {zip_name} items={len(items)} by {current_user.get('name')}"
    )
    append_audit_record(
        AuditRecord(
            ts=datetime.now().timestamp(),
            action="compress",
            path=f"{safe_rel}/{zip_name}" if safe_rel else zip_name,
            spaceType=space_type,
            departmentId=department_id,
            clientIp=client_ip,
            detail={"count": len(items), "editor": current_user.get("name")},
        )
    )

    return {"success": True}