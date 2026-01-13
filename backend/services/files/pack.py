from typing import Optional, Dict, Any, List
import io
import os
from pathlib import Path
from datetime import datetime
import zipfile
from urllib.parse import quote, parse_qs

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from ...config import SpaceType, PACK_MAX_SIZE_BYTES
from .base import resolve_root, write_log, ensure_department_read_access
from ...routers.audit import append_audit_record, AuditRecord, touch_download_meta


async def pack_download_dir(
    request: Request,
    spaceType: Optional[str],
    departmentId: Optional[str],
    path: str,
    name: Optional[str],
    pack: int,
    current_user: dict,
):
    """对应 legacy 中 @router.get('/pack') 的实现。"""
    if not pack:
        raise HTTPException(status_code=400, detail="缺少 pack=1 参数")

    # 从原始 scope 中取 query_string，用于解析 items[...]
    raw_qs = request.scope.get("query_string", b"").decode("utf-8")

    # 检测是否存在 items[0][...] 形式参数
    has_items = "items%5B0%5D%5B" in raw_qs or "items[0][" in raw_qs

    if has_items:
        # 多附件打包：解析 items[i][field]
        qs = parse_qs(raw_qs, keep_blank_values=True)
        # 收集所有 index
        idx_set = set()
        for key in qs.keys():
            if key.startswith("items["):
                try:
                    inner = key[len("items["):]
                    idx = int(inner.split("]")[0])
                    idx_set.add(idx)
                except Exception:
                    continue
        if not idx_set:
            raise HTTPException(status_code=400, detail="缺少打包文件列表")

        mem = io.BytesIO()
        added_count = 0
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx in sorted(idx_set):
                base_key = f"items[{idx}]"

                def get_val(field: str) -> str:
                    k1 = f"{base_key}[{field}]"
                    return qs.get(k1, [""])[0]

                it_space = get_val("spaceType") or None
                it_dept = get_val("departmentId") or None
                it_path = get_val("path") or ""
                it_name = get_val("name") or ""
                if not it_space or not it_name:
                    continue
                # 逐项读权限校验：部门空间必须具备读权限
                if it_space == SpaceType.DEPARTMENT:
                    ensure_department_read_access(it_dept or '', current_user)

                base_dir = resolve_root(it_space, it_dept or None, current_user)
                safe_rel = Path(it_path).as_posix().lstrip("/")
                file_path = (base_dir / safe_rel / it_name).resolve()
                try:
                    file_path.relative_to(base_dir.resolve())
                except ValueError:
                    continue
                if not file_path.is_file():
                    continue
                zf.write(file_path, it_name)
                added_count += 1

        if added_count == 0:
            raise HTTPException(status_code=400, detail="未找到可打包的文件，请检查附件是否已被移动或删除")

        mem.seek(0)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"附件-{ts}.zip"
        safe_name = quote(fname.encode("utf-8"))
        return StreamingResponse(
            mem,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={safe_name}; filename*=UTF-8''{safe_name}",
            },
        )

    # 无 items[...] 时：保持原有“单目录打包”行为
    if not spaceType:
        raise HTTPException(status_code=400, detail="缺少 spaceType 参数")
    if name is None:
        raise HTTPException(status_code=400, detail="缺少 name 参数")

    base_dir = resolve_root(spaceType, departmentId, current_user)
    safe_rel = Path(path).as_posix().lstrip("/")
    target_dir = (base_dir / safe_rel / name).resolve()
    try:
        target_dir.relative_to(base_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径")
    if not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="只能对文件夹执行目录打包")

    mem = io.BytesIO()
    added_count = 0
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in target_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(base_dir)
                zf.write(file_path, arcname.as_posix())
                added_count += 1

    if added_count == 0:
        raise HTTPException(status_code=400, detail="目标目录下没有可打包的文件")

    mem.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"附件-{ts}.zip"
    safe_name = quote(fname.encode("utf-8"))
    return StreamingResponse(
        mem,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={safe_name}; filename*=UTF-8''{safe_name}",
        },
    )


async def pack_download_multi(body: Dict[str, Any], current_user: dict):
    """body 结构与 PackRequest 相同：{"title": str|None, "items": [{...}]}"""
    items = body.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="缺少打包文件列表")

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for it in items:
            space_type = it.get("spaceType")
            department_id = it.get("departmentId")
            it_path = it.get("path") or ""
            name = it.get("name") or ""
            # 逐项读权限校验
            if space_type == SpaceType.DEPARTMENT:
                ensure_department_read_access(department_id or '', current_user)

            base_dir = resolve_root(space_type, department_id, current_user)
            file_path = base_dir / it_path / name
            if not file_path.is_file():
                continue
            zf.write(file_path, name)

    mem.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"附件-{ts}.zip"
    safe_name = quote(fname.encode("utf-8"))
    return StreamingResponse(
        mem,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={safe_name}; filename*=UTF-8''{safe_name}",
        },
    )


async def pack_to_temp(body: Dict[str, Any], current_user: dict) -> Dict[str, Any]:
    """body 结构与 PackTempRequest 相同，返回结构与 PackTempResponse 相同。"""
    items = body.get("items") or []
    title = (body.get("title") or "").strip()
    if not items:
        raise HTTPException(status_code=400, detail="缺少打包文件列表")

    # 检查总大小是否超过配置的限制
    MAX_PACK_SIZE = PACK_MAX_SIZE_BYTES
    total_size = 0
    for it in items:
        space_type = it.get("spaceType")
        department_id = it.get("departmentId")
        it_path = it.get("path") or ""
        name = it.get("name") or ""

        # 逐项读权限校验：部门空间必须具备读权限
        if space_type == SpaceType.DEPARTMENT:
            ensure_department_read_access(department_id or '', current_user)

        base_dir = resolve_root(space_type, department_id, current_user)
        safe_rel = Path(it_path).as_posix().lstrip("/")
        src_path = (base_dir / safe_rel / name).resolve()
        try:
            src_path.relative_to(base_dir.resolve())
        except ValueError:
            continue
        if not src_path.exists():
            continue
        
        # 计算文件/文件夹大小
        if src_path.is_dir():
            for dirpath, _, filenames in os.walk(src_path):
                for fname in filenames:
                    full = Path(dirpath) / fname
                    total_size += full.stat().st_size
        else:
            total_size += src_path.stat().st_size

    if total_size > MAX_PACK_SIZE:
        limit_gb = MAX_PACK_SIZE / 1024 / 1024 / 1024
        raise HTTPException(status_code=413, detail=f"超过{limit_gb:.2f}GB大小限制，当前大小：{total_size / 1024 / 1024 / 1024:.2f}GB")

    public_root = resolve_root(SpaceType.PUBLIC, None, current_user)
    pack_dir = public_root / "__packs__"
    pack_dir.mkdir(parents=True, exist_ok=True)

    # 兜底清理：删除过期临时包
    import time

    now_ts = time.time()
    expire_seconds = 3600
    try:
        for entry in pack_dir.iterdir():
            if not entry.is_file():
                continue
            lower_name = entry.name.lower()
            if not lower_name.endswith(".zip"):
                continue
            stat = entry.stat()
            if now_ts - stat.st_mtime > expire_seconds:
                entry.unlink(missing_ok=True)
    except Exception:
        pass

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if title:
        safe_title = title.replace("/", "_").replace("\\", "_")[:40]
        zip_name = f"{safe_title}_{ts}.zip"
    else:
        zip_name = f"hbcloud_{ts}.zip"

    zip_path = (pack_dir / zip_name).resolve()
    if zip_path.exists():
        if zip_path.is_dir():
            import shutil as _shutil

            _shutil.rmtree(zip_path, ignore_errors=True)
        else:
            zip_path.unlink(missing_ok=True)

    missing_count = 0
    added_count = 0
    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for it in items:
            space_type = it.get("spaceType")
            department_id = it.get("departmentId")
            it_path = it.get("path") or ""
            name = it.get("name") or ""

            # 逐项读权限校验：部门空间必须具备读权限
            if space_type == SpaceType.DEPARTMENT:
                ensure_department_read_access(department_id or '', current_user)

            base_dir = resolve_root(space_type, department_id, current_user)
            safe_rel = Path(it_path).as_posix().lstrip("/")
            src_path = (base_dir / safe_rel / name).resolve()
            try:
                src_path.relative_to(base_dir.resolve())
            except ValueError:
                missing_count += 1
                continue
            if not src_path.exists():
                missing_count += 1
                continue
            if src_path.is_dir():
                for dirpath, _, filenames in os.walk(src_path):
                    base = Path(dirpath)
                    for fname in filenames:
                        full = base / fname
                        rel = full.relative_to(base_dir).as_posix()
                        zf.write(full, rel)
                        added_count += 1
                        from ...routers.audit import log_action  # 延迟导入
                        log_action(
                            action="zip",
                            path=rel,
                            spaceType=space_type,
                            departmentId=department_id,
                            clientIp="",
                            detail={"fromPackTemp": True},
                            text_message=(
                                f"pack-temp zip {space_type} {department_id or ''} {rel} title={title or ''} by {current_user.get('name')}"
                            ),
                        )
                        from pathlib import Path as _P
                        touch_download_meta(space_type, department_id, _P(rel).parent.as_posix(), _P(rel).name, datetime.now().timestamp())
            else:
                rel = src_path.relative_to(base_dir).as_posix()
                zf.write(src_path, rel)
                added_count += 1
                from ...routers.audit import log_action  # 延迟导入
                log_action(
                    action="zip",
                    path=rel,
                    spaceType=space_type,
                    departmentId=department_id,
                    clientIp="",
                    detail={"fromPackTemp": True},
                    text_message=(
                        f"pack-temp zip {space_type} {department_id or ''} {rel} title={title or ''} by {current_user.get('name')}"
                    ),
                )
                from pathlib import Path as _P
                touch_download_meta(space_type, department_id, _P(rel).parent.as_posix(), _P(rel).name, datetime.now().timestamp())

    if added_count == 0:
        try:
            if zip_path.exists():
                zip_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="未找到可打包的文件，请检查附件是否已被移动或删除")

    from ...routers.audit import log_action  # 延迟导入
    text = (
        f"pack-temp items={len(items)} missing={missing_count} title={title or ''} by {current_user.get('name')}"
        if missing_count
        else f"pack-temp items={len(items)} title={title or ''} by {current_user.get('name')}"
    )
    log_action(
        action="pack-temp",
        path=f"__packs__/{zip_name}",
        spaceType=SpaceType.PUBLIC,
        departmentId=None,
        clientIp="",
        detail={
            "items": len(items),
            "missing": missing_count,
            "title": title or "",
            "editor": current_user.get("name"),
        },
        text_message=text,
    )
    return {
        "spaceType": SpaceType.PUBLIC,
        "departmentId": None,
        "path": "__packs__",
        "name": zip_name,
        "missingCount": missing_count,
    }