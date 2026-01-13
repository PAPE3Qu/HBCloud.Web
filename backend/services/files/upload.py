from pathlib import Path
from typing import List, Optional, Dict, Any
import hashlib
import json
import shutil
from datetime import datetime

from fastapi import HTTPException, UploadFile, Request, File

from ...config import DATA_ROOT, SpaceType
from .base import resolve_root, write_log, ensure_department_write_access
from ...routers.audit import append_audit_record, AuditRecord, touch_edit_meta


# 兼容 legacy 中的临时大文件目录结构
_BIG_UPLOAD_ROOT = DATA_ROOT / "tmp_big_uploads"
_BIG_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def _get_big_upload_dir(upload_id: str) -> Path:
    return _BIG_UPLOAD_ROOT / upload_id


async def upload_files(
    request: Request,
    spaceType: str,
    departmentId: Optional[str],
    path: str,
    files: List[UploadFile],
    md5: Optional[List[str]],
    current_user: dict,
):
    """对应 legacy 中 @router.post("/upload") 的实现，去掉 Form/Depends 包装。"""
    # 1) 先做部门空间写权限检查（若是部门空间）
    if spaceType == SpaceType.DEPARTMENT:
        ensure_department_write_access(departmentId or '', current_user)

    # 2) 再解析根目录与路径，进入写入逻辑
    root = resolve_root(spaceType, departmentId, current_user)
    safe_rel = Path(path).as_posix().lstrip("/")

    # 对普通用户 safe 空间，若前端仍传入手机号路径，则当作根目录处理
    if spaceType == SpaceType.SAFE and current_user.get("role") != "super":
        phone = (current_user.get("phone") or "").strip()
        if safe_rel == phone:
            safe_rel = ""

    target_dir = (root / safe_rel).resolve()

    try:
        target_dir.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径")

    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="目标目录不存在")

    saved: List[str] = []
    for idx, f in enumerate(files):
        filename = Path(f.filename).name
        if not filename:
            continue
        dest = target_dir / filename
        if dest.exists():
            raise HTTPException(status_code=400, detail=f"文件已存在: {filename}")
        with dest.open("wb") as out:
            while True:
                chunk = await f.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        # 如提供 md5，则对刚写入的文件进行完整性校验
        expected_md5 = None
        if md5 and idx < len(md5):
            expected_md5 = (md5[idx] or "").strip().lower() or None
        if expected_md5:
            m = hashlib.md5()
            with dest.open("rb") as check_f:
                for buf in iter(lambda: check_f.read(1024 * 1024), b""):
                    m.update(buf)
            actual_md5 = m.hexdigest().lower()
            if actual_md5 != expected_md5:
                # 校验失败：删除该文件并报错
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=500, detail=f"文件校验失败（MD5 不一致）：{filename}")
        saved.append(filename)

    # 审计：上传
    client_ip = request.client.host if request.client else ""
    now = datetime.now().timestamp()
    from ...routers.audit import log_action  # 延迟导入避免循环依赖
    for fname in saved:
        # 更新文件详情索引：上传视为一次编辑
        touch_edit_meta(spaceType, departmentId, safe_rel, fname, current_user.get("name"), now)
        log_action(
            action="upload",
            path=f"{safe_rel}/{fname}" if safe_rel else fname,
            spaceType=spaceType,
            departmentId=departmentId,
            clientIp=client_ip,
            detail={"size": None, "editor": current_user.get("name")},
            text_message=(
                f"upload {spaceType} {departmentId or ''} {safe_rel}/{fname} "
                f"by {current_user.get('name')} from {client_ip}"
            ),
        )
    return {"success": True, "files": saved}


async def big_upload_init(payload, current_user: dict):
    """对应 legacy 中 big_upload_init，payload 为 BigUploadInitRequest。"""
    from ...routers.files import BigUploadInitResponse  # type: ignore

    # 1) 先做部门空间写权限检查
    if payload.spaceType == SpaceType.DEPARTMENT:
        ensure_department_write_access(payload.departmentId or '', current_user)

    # 2) 再解析根目录和目标路径
    root = resolve_root(payload.spaceType, payload.departmentId, current_user)
    safe_rel = Path(payload.path).as_posix().lstrip("/")
    target_dir = (root / safe_rel).resolve()
    try:
        target_dir.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径")
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="目标目录不存在")

    upload_id = hashlib.md5(f"{payload.fileName}-{payload.size}-{datetime.utcnow().timestamp()}".encode("utf-8")).hexdigest()
    up_dir = _get_big_upload_dir(upload_id)
    up_dir.mkdir(parents=True, exist_ok=True)
    meta: Dict[str, Any] = {
        "spaceType": payload.spaceType,
        "departmentId": payload.departmentId,
        "path": safe_rel,
        "fileName": payload.fileName,
        "size": payload.size,
        "fileMd5": (payload.fileMd5 or "").lower() or None,
        "createdAt": datetime.utcnow().timestamp(),
    }
    (up_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    # 推荐分片大小：50MB
    chunk_size = 50 * 1024 * 1024
    return BigUploadInitResponse(uploadId=upload_id, chunkSize=chunk_size)


async def big_upload_chunk(uploadId: str, index: int, total: int, chunk: UploadFile, current_user: dict):
    """对应 legacy 中 big_upload_chunk。"""
    up_dir = _get_big_upload_dir(uploadId)
    if not up_dir.exists() or not up_dir.is_dir():
        raise HTTPException(status_code=404, detail="上传任务不存在或已过期")
    # 简单权限防护：根据 meta 重新解析目标根目录，确保当前用户仍有权限
    try:
        meta = json.loads((up_dir / "meta.json").read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="上传元数据损坏")
    _ = resolve_root(meta.get("spaceType") or "public", meta.get("departmentId"), current_user)
    part_path = up_dir / f"{index}.part"
    with part_path.open("wb") as out:
        while True:
            data = await chunk.read(1024 * 1024)
            if not data:
                break
            out.write(data)
    from ...routers.files import BigUploadChunkResponse  # type: ignore
    return BigUploadChunkResponse(received=True, index=index)


async def big_upload_complete(payload, current_user: dict):
    """对应 legacy 中 big_upload_complete。payload 为 BigUploadCompleteRequest。"""
    up_dir = _get_big_upload_dir(payload.uploadId)
    if not up_dir.exists() or not up_dir.is_dir():
        raise HTTPException(status_code=404, detail="上传任务不存在或已过期")

    # 1) 先读取 meta 并完成部门空间写权限检查
    try:
        meta = json.loads((up_dir / "meta.json").read_text(encoding="utf-8"))
    except Exception:
        shutil.rmtree(up_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="上传元数据损坏")

    space_type = meta.get("spaceType") or "public"
    department_id = meta.get("departmentId")
    if space_type == SpaceType.DEPARTMENT:
        ensure_department_write_access(department_id or '', current_user)

    # 2) 权限通过后，再解析根目录与目标路径，执行合并/校验/写入
    try:
        rel_path = meta.get("path") or ""
        file_name = meta.get("fileName") or "uploaded.bin"
        expected_size = int(meta.get("size") or 0)
        expected_md5 = meta.get("fileMd5") or None

        root = resolve_root(space_type, department_id, current_user)
        target_dir = (root / rel_path).resolve()
        try:
            target_dir.relative_to(root.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="非法路径")
        if not target_dir.exists() or not target_dir.is_dir():
            raise HTTPException(status_code=404, detail="目标目录不存在")

        # 收集所有分片索引
        part_indices: List[int] = []
        for p in up_dir.iterdir():
            if p.is_file() and p.name.endswith(".part"):
                try:
                    idx = int(p.stem)
                    part_indices.append(idx)
                except ValueError:
                    continue
        if not part_indices:
            raise HTTPException(status_code=400, detail="未找到任何分片，请重试上传")
        part_indices.sort()

        final_path = (target_dir / file_name).resolve()
        try:
            final_path.relative_to(root.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="非法路径")
        if final_path.exists():
            raise HTTPException(status_code=400, detail="目标文件已存在，请先删除或重命名后再上传")

        # 合并分片
        with final_path.open("wb") as out:
            for idx in part_indices:
                part_file = up_dir / f"{idx}.part"
                if not part_file.exists():
                    raise HTTPException(status_code=400, detail="分片不完整，请重试上传")
                with part_file.open("rb") as pf:
                    shutil.copyfileobj(pf, out)

        # 大小校验（允许 1MB 内误差）
        actual_size = final_path.stat().st_size
        if expected_size and abs(actual_size - expected_size) > 1024 * 1024:
            try:
                final_path.unlink(missing_ok=True)
            finally:
                raise HTTPException(status_code=500, detail="文件大小校验失败，请重试上传")

        # 可选 MD5 校验
        if expected_md5:
            md5 = hashlib.md5()
            with final_path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    md5.update(chunk)
            actual_md5 = md5.hexdigest().lower()
            if actual_md5 != expected_md5:
                try:
                    final_path.unlink(missing_ok=True)
                finally:
                    raise HTTPException(status_code=500, detail="文件校验失败（MD5 不一致），请重试上传")

        # 审计：大文件上传完成视为一次 upload 行为
        from ...routers.audit import log_action  # 延迟导入
        log_action(
            action="upload",
            path=f"{rel_path}/{file_name}" if rel_path else file_name,
            spaceType=space_type,
            departmentId=department_id,
            clientIp="",
            detail={"size": actual_size, "editor": current_user.get("name")},
            text_message=(
                f"big_upload_complete {space_type} {department_id or ''} {rel_path}/{file_name} "
                f"by {current_user.get('name')}"
            ),
        )
        # 更新索引：上传视为一次编辑
        touch_edit_meta(space_type, department_id, rel_path, file_name, current_user.get("name"), datetime.now().timestamp())
    finally:
        # 清理临时目录
        shutil.rmtree(up_dir, ignore_errors=True)

    return {"success": True}


async def big_upload_abort(payload, current_user: dict):
    """对应 legacy 中 big_upload_abort。payload 为 BigUploadAbortRequest。"""
    up_dir = _get_big_upload_dir(payload.uploadId)
    if not up_dir.exists() or not up_dir.is_dir():
        return {"success": True}
    # 简单权限校验：如果 meta 可读，则调用 resolve_root 校验当前用户是否仍有权
    try:
        meta = json.loads((up_dir / "meta.json").read_text(encoding="utf-8"))
        _ = resolve_root(meta.get("spaceType") or "public", meta.get("departmentId"), current_user)
    except Exception:
        pass
    shutil.rmtree(up_dir, ignore_errors=True)
    return {"success": True}