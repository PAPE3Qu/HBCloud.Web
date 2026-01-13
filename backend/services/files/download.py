from pathlib import Path
from typing import Optional, Dict, Any, List
import io
import os
from datetime import datetime
from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from ...config import SpaceType
from .base import resolve_root, write_log
from ...routers.audit import append_audit_record, AuditRecord, touch_download_meta


async def download_file(
    request: Request,
    spaceType: str,
    departmentId: Optional[str],
    path: str,
    name: str,
    disposition: str,
    current_user: dict,
):
    """对应 legacy 中 @router.api_route("/download") 实现。"""
    root = resolve_root(spaceType, departmentId, current_user)
    # 规范化 path
    raw_path = path or ""
    if raw_path in ("", ".", "./"):
        safe_rel = ""
    else:
        safe_rel = Path(raw_path).as_posix().lstrip("/")

    # SAFE 空间普通用户手机号路径兼容
    if spaceType == SpaceType.SAFE and current_user.get("role") != "super":
        phone = (current_user.get("phone") or "").strip()
        if safe_rel == phone:
            safe_rel = ""

    file_path = (root / safe_rel / name).resolve()

    try:
        file_path.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    def iter_file():
        nonlocal file_path
        try:
            with file_path.open("rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    yield chunk
        finally:
            # 若为公共空间下的临时打包文件，则在下载结束后尝试删除
            try:
                lower_name = name.lower()
                rel = safe_rel
                if (
                    spaceType == SpaceType.PUBLIC
                    and (rel == "__packs__" or rel == "/__packs__" or rel.endswith("/__packs__"))
                    and lower_name.endswith(".zip")
                ):
                    file_path.unlink(missing_ok=True)
            except Exception:
                pass

    # 审计：下载（仅对 GET 记为真实访问；HEAD 只探测不计数）
    client_ip = request.client.host if request.client else ""
    now = datetime.now().timestamp()
    rel_path = Path(path).as_posix().lstrip("/")
    if request.method == "GET":
        from ...routers.audit import log_action  # 延迟导入
        log_action(
            action="download",
            path=f"{rel_path}/{name}" if rel_path else name,
            spaceType=spaceType,
            departmentId=departmentId,
            clientIp=client_ip,
            detail={"disposition": disposition},
            text_message=(
                f"download {spaceType} {departmentId or ''} {rel_path}/{name} "
                f"disposition={disposition} by {current_user.get('name')} from {client_ip}"
            ),
        )
        touch_download_meta(spaceType, departmentId, rel_path, name, now)

    # 推断 mime
    lower = file_path.name.lower()
    if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
        mime = "image/" + lower.split(".")[-1].replace("jpg", "jpeg")
    elif lower.endswith(".svg"):
        mime = "image/svg+xml"
    elif lower.endswith(".pdf"):
        mime = "application/pdf"
    else:
        mime = "application/octet-stream"

    disp = "inline" if disposition == "inline" else "attachment"
    safe_name = quote(file_path.name.encode("utf-8"))
    headers = {
        "Content-Disposition": f"{disp}; filename={safe_name}; filename*=UTF-8''{safe_name}"
    }

    if request.method == "HEAD":
        # 仅返回头部，不返回实体
        return StreamingResponse(iter(lambda: b"", 1), media_type=mime, headers=headers)

    return StreamingResponse(iter_file(), media_type=mime, headers=headers)


async def download_zip(request: Request, payload: dict, current_user: dict):
    """对应 legacy 中 @router.post("/download-zip")。payload 形如 {"items": [...]}"""
    items = payload.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="未选择任何项")

    mem_file = io.BytesIO()

    with zipfile.ZipFile(mem_file, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:  # type: ignore[name-defined]
        for item in items:
            space_type = item.get("spaceType")
            department_id = item.get("departmentId")
            rel_path = item.get("path") or ""
            name = item.get("name") or ""
            is_dir = bool(item.get("is_dir"))

            root = resolve_root(space_type, department_id, current_user)
            safe_rel = Path(rel_path).as_posix().lstrip("/")
            src_path = (root / safe_rel / name).resolve()

            try:
                src_path.relative_to(root.resolve())
            except ValueError:
                continue

            if not src_path.exists():
                continue

            if src_path.is_dir():
                # 先写入目录本身（支持空目录）
                rel_dir = src_path.relative_to(root).as_posix().rstrip("/") + "/"
                zf.writestr(rel_dir, "")
                for dirpath, dirnames, filenames in os.walk(src_path):
                    base = Path(dirpath)
                    # 为空的子目录也写入一条目录记录
                    for d in dirnames:
                        full_d = base / d
                        rel_d = full_d.relative_to(root).as_posix().rstrip("/") + "/"
                        zf.writestr(rel_d, "")
                    for fname in filenames:
                        full_path = base / fname
                        rel_f = full_path.relative_to(root)
                        zf.write(full_path, rel_f.as_posix())
            else:
                rel_f = src_path.relative_to(root)
                zf.write(src_path, rel_f.as_posix())

    # 审计：打包下载 -> 视为对源文件的一次下载
    client_ip = request.client.host if request.client else ""
    now = datetime.now().timestamp()
    from ...routers.audit import log_action  # 延迟导入
    for item in items:
        space_type = item.get("spaceType")
        department_id = item.get("DepartmentId") if "DepartmentId" in item else item.get("departmentId")
        # 兼容大小写字段
        if department_id is None:
            department_id = item.get("departmentId")
        rel = Path(item.get("path") or "").as_posix().lstrip("/")
        name = item.get("name") or ""
        is_dir = bool(item.get("is_dir"))
        full = f"{rel}/{name}" if rel else name
        log_action(
            action="zip",
            path=full,
            spaceType=space_type,
            departmentId=department_id,
            clientIp=client_ip,
            detail={"isDir": is_dir},
            text_message=(
                f"zip_download {space_type} {department_id or ''} {full} "
                f"isDir={is_dir} by {current_user.get('name')} from {client_ip}"
            ),
        )
        if not is_dir:
            touch_download_meta(space_type, department_id, rel, name, now)

    mem_file.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    headers = {"Content-Disposition": f"attachment; filename=hbcloud_{ts}.zip"}
    return StreamingResponse(mem_file, media_type="application/zip", headers=headers)