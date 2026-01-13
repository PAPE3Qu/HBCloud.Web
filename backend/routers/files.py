from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ..config import SpaceType, DEPT_ROOT
from .auth import get_current_user, pwd_context
from ..services.files.base import resolve_root, write_log
from ..services.files import dept as dept_svc
from ..services.files import listing as listing_svc
from ..services.files import upload as upload_svc
from ..services.files import download as download_svc
from ..services.files import pack as pack_svc
from ..services.files import pack_async as pack_async_svc
from ..services.files import operations as ops_svc
from ..services.files import search_zip as search_zip_svc
from ..services.files import recycle as recycle_svc
from ..services.files import dept_roles as dept_roles_svc
from ..services.files import favorites as favorites_svc
from ..routers import audit as audit_router  # 仅为类型提示，不在此使用

router = APIRouter(tags=["files"])


class Department(BaseModel):
    id: str
    name: str


class CreateDeptRequest(BaseModel):
    id: str
    name: str
    deletePassword: str


class DeleteDeptRequest(BaseModel):
    id: str
    deletePassword: str


class FolderCreateRequest(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str = ""
    folderName: str


class FileItem(BaseModel):
    name: str
    is_dir: bool
    size: int
    modified_time: float


class FileListResponse(BaseModel):
    current_path: str
    items: List[FileItem]


class DeleteItem(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str = ""
    name: str
    is_dir: bool


class DeleteRequest(BaseModel):
    items: List[DeleteItem]


class RenameRequest(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str = ""
    oldName: str
    newName: str
    isDir: bool


class SearchItem(BaseModel):
    name: str
    is_dir: bool
    size: int
    modified_time: float
    path: str


class PackItem(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: Optional[str] = ''
    name: str


class PackRequest(BaseModel):
    title: Optional[str] = None
    items: List[PackItem]


class MoveItem(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str = ''
    name: str
    is_dir: bool


class MoveRequest(BaseModel):
    items: List[MoveItem]
    targetSpaceType: str
    targetDepartmentId: Optional[str] = None
    targetPath: str = ''
    overwrite: bool = False


class CopyItem(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str = ''
    name: str
    is_dir: bool


class CopyRequest(BaseModel):
    items: List[CopyItem]
    targetSpaceType: str
    targetDepartmentId: Optional[str] = None
    targetPath: str = ''
    overwrite: bool = False


class UnzipRequest(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str = ""
    name: str
    overwrite: bool = False


class BigUploadInitRequest(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str = ""
    fileName: str
    size: int
    fileMd5: Optional[str] = None


class BigUploadInitResponse(BaseModel):
    uploadId: str
    chunkSize: int


class BigUploadChunkResponse(BaseModel):
    received: bool
    index: int


class BigUploadCompleteRequest(BaseModel):
    uploadId: str


class BigUploadAbortRequest(BaseModel):
    uploadId: str


class RecycleItem(BaseModel):
    id: int
    scope: str
    spaceType: str
    departmentId: Optional[str] = None
    originalPath: str
    name: str
    isDir: bool
    deletedAt: float
    deletedBy: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class RecycleListResponse(BaseModel):
    items: List[RecycleItem]
    total: int


class RecycleIdsRequest(BaseModel):
    ids: List[int]


class PackTempItem(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: Optional[str] = ''
    name: str


class PackTempRequest(BaseModel):
    title: Optional[str] = None
    items: List[PackTempItem]


class PackTempResponse(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str
    name: str
    missingCount: int = 0


class CompressItem(BaseModel):
    name: str
    is_dir: bool


class CompressRequest(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str = ""
    zipName: str
    items: List[CompressItem]


class UpdateDeptConfigRequest(BaseModel):
    isOpen: bool


class DeptRoleUser(BaseModel):
    phone: str
    name: str


class DeptRolesResponse(BaseModel):
    dept: List[DeptRoleUser]
    member: List[DeptRoleUser]


class UpdateDeptRolesRequest(BaseModel):
    admins: List[str] = []
    members: List[str] = []


class FavoriteItem(BaseModel):
    id: Optional[int] = None
    spaceType: str
    departmentId: Optional[str] = None
    path: str
    displayName: Optional[str] = None


@router.get("/spaces", response_model=List[str])
async def list_spaces():
    return dept_svc.list_spaces()


@router.get("/departments", response_model=List[Department])
async def list_departments():
    return dept_svc.list_departments()


@router.post("/departments", response_model=Department)
async def create_department(payload: CreateDeptRequest, current_user: dict = Depends(get_current_user)):
    return dept_svc.create_department(payload, current_user)


@router.delete("/departments")
async def delete_department(payload: DeleteDeptRequest, current_user: dict = Depends(get_current_user)):
    return dept_svc.delete_department(payload, current_user)


@router.get("/departments/{dept_id}/config")
async def get_department_config(dept_id: str, current_user: dict = Depends(get_current_user)):
    """获取指定部门的配置详情，供空间权限页面使用。"""
    # 目前不做额外权限限制，后续如需可根据 current_user.role 等扩展
    return dept_svc.get_department_config(dept_id)


@router.put("/departments/{dept_id}/config")
async def update_department_config(
    dept_id: str,
    payload: UpdateDeptConfigRequest,
    current_user: dict = Depends(get_current_user),
):
    """更新部门空间配置，目前仅支持更新 isOpen 字段。

    权限策略：
    - super / op 可以修改任意部门配置；
    - 部门管理员（dept）只能修改自己所在部门的配置。
    """
    # 先获取当前配置，便于做权限判断和审计
    cfg = dept_svc.get_department_config(dept_id)

    # 权限检查
    role = current_user.get("role")
    current_phone = current_user.get("phone") or ""
    if role not in ("super", "op"):
        # 非 super/op，要求是该部门的部门管理员
        from ..services.files import dept_roles as dept_roles_svc  # type: ignore

        dept_role = dept_roles_svc.get_user_dept_role(current_phone, dept_id)
        if dept_role != "dept":
            raise HTTPException(status_code=403, detail="无权限修改该部门配置")

    # 计算变更前后
    before_is_open = bool(cfg.get("isOpen", True))
    after_is_open = bool(payload.isOpen)
    if before_is_open == after_is_open:
        # 没有实际变更，直接返回当前配置
        return cfg

    # 写回 config.json
    from ..services.files.dept import _read_dept_config, _write_dept_config  # type: ignore
    from datetime import datetime

    dept_dir = DEPT_ROOT / dept_id
    if not dept_dir.exists() or not dept_dir.is_dir():
        raise HTTPException(status_code=404, detail="部门不存在")

    raw_cfg = _read_dept_config(dept_dir) or {}
    raw_cfg["isOpen"] = after_is_open
    _write_dept_config(dept_dir, raw_cfg)

    # 写审计记录（结构化 JSON）
    from .audit import append_audit_record, AuditRecord  # type: ignore

    now_ts = datetime.now().timestamp()
    append_audit_record(
        AuditRecord(
            ts=now_ts,
            action="space_config",
            path=dept_id,
            spaceType=SpaceType.DEPARTMENT,
            departmentId=dept_id,
            clientIp="",
            detail={
                "deptId": dept_id,
                "isOpenBefore": before_is_open,
                "isOpenAfter": after_is_open,
                "updatedBy": current_phone,
                "reason": "update_isOpen",
            },
        )
    )
    # 补一行文本日志，方便 grep
    write_log(
        f"space_config dept={dept_id} isOpen {before_is_open} -> {after_is_open} updatedBy={current_phone}"
    )

    # 返回最新配置（走已有 service，确保字段一致）
    return dept_svc.get_department_config(dept_id)


@router.get("/departments/{dept_id}/roles", response_model=DeptRolesResponse)
async def get_department_roles(
    dept_id: str,
    current_user: dict = Depends(get_current_user),
):
    """获取指定部门的管理员/成员列表。

    当前策略：登录用户即可查看；如需收紧，可限制为 super/op/dept。
    """
    roles = dept_roles_svc.get_dept_roles(dept_id)
    return roles


@router.put("/departments/{dept_id}/roles")
async def update_department_roles(
    dept_id: str,
    payload: UpdateDeptRolesRequest,
    current_user: dict = Depends(get_current_user),
):
    """更新指定部门的管理员/成员列表。

    权限策略：
    - super / op 可以修改任意部门；
    - 部门管理员（dept）只能修改自己所在部门的角色列表。
    """
    # 权限检查
    role = current_user.get("role")
    current_phone = current_user.get("phone") or ""
    if role not in ("super", "op"):
        dept_role = dept_roles_svc.get_user_dept_role(current_phone, dept_id)
        if dept_role != "dept":
            raise HTTPException(status_code=403, detail="无权限修改该部门成员配置")

    # 读写角色列表
    result = dept_roles_svc.set_dept_roles(
        dept_id,
        admins=payload.admins or [],
        members=payload.members or [],
        updated_by=current_phone,
    )

    # 写审计记录（结构化 JSON）
    from datetime import datetime
    from .audit import append_audit_record, AuditRecord  # type: ignore

    now_ts = datetime.now().timestamp()
    before_admins = result["before"]["dept"]
    after_admins = result["after"]["dept"]
    before_members = result["before"]["member"]
    after_members = result["after"]["member"]

    append_audit_record(
        AuditRecord(
            ts=now_ts,
            action="space_config",
            path=dept_id,
            spaceType=SpaceType.DEPARTMENT,
            departmentId=dept_id,
            clientIp="",
            detail={
                "deptId": dept_id,
                "adminsBefore": before_admins,
                "adminsAfter": after_admins,
                "membersBefore": before_members,
                "membersAfter": after_members,
                "updatedBy": current_phone,
                "reason": "update_roles",
            },
        )
    )
    # 文本日志摘要一行
    write_log(
        "space_roles dept=%s admins %s -> %s members %s -> %s updatedBy=%s"
        % (
            dept_id,
            ",".join(before_admins or []),
            ",".join(after_admins or []),
            ",".join(before_members or []),
            ",".join(after_members or []),
            current_phone,
        )
    )

    # 返回最新角色列表，便于前端刷新
    return dept_roles_svc.get_dept_roles(dept_id)


@router.get("/list", response_model=FileListResponse)
async def list_files(
    request: Request,
    spaceType: str = Query(...),
    departmentId: Optional[str] = Query(None),
    path: str = Query(""),
    current_user: dict = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else ""
    return await listing_svc.list_files(spaceType, departmentId, path, current_user, client_ip)


@router.get("/dir-size")
async def get_dir_size(
    spaceType: str = Query(...),
    departmentId: Optional[str] = Query(None),
    path: str = Query(""),
    name: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """计算指定目录的总大小（包含子目录中的所有文件）"""
    return await listing_svc.get_directory_size(spaceType, departmentId, path, name, current_user)


@router.post("/folder")
async def create_folder(request: Request, payload: FolderCreateRequest, current_user: dict = Depends(get_current_user)):
    client_ip = request.client.host if request.client else ""
    # 传 dict 给 service，内部用 payload.get 访问
    data = payload.dict()
    return await ops_svc.create_folder(data, current_user, client_ip)


@router.post("/upload")
async def upload_files(
    request: Request,
    spaceType: str = Form(...),
    departmentId: Optional[str] = Form(None),
    path: str = Form(""),
    files: List[UploadFile] = File(...),
    md5: Optional[List[str]] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    return await upload_svc.upload_files(request, spaceType, departmentId, path, files, md5, current_user)


@router.post("/big/init", response_model=BigUploadInitResponse)
async def big_upload_init(payload: BigUploadInitRequest, current_user: dict = Depends(get_current_user)):
    return await upload_svc.big_upload_init(payload, current_user)


@router.post("/big/chunk", response_model=BigUploadChunkResponse)
async def big_upload_chunk(
    uploadId: str = Form(...),
    index: int = Form(...),
    total: int = Form(...),
    chunk: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    return await upload_svc.big_upload_chunk(uploadId, index, total, chunk, current_user)


@router.post("/big/complete")
async def big_upload_complete(payload: BigUploadCompleteRequest, current_user: dict = Depends(get_current_user)):
    return await upload_svc.big_upload_complete(payload, current_user)


@router.post("/big/abort")
async def big_upload_abort(payload: BigUploadAbortRequest, current_user: dict = Depends(get_current_user)):
    return await upload_svc.big_upload_abort(payload, current_user)


@router.api_route("/download", methods=["GET", "HEAD"])
async def download_file(
    request: Request,
    spaceType: str = Query(...),
    departmentId: Optional[str] = Query(None),
    path: str = Query(""),
    name: str = Query(...),
    disposition: str = Query("attachment"),
    current_user: dict = Depends(get_current_user),
):
    return await download_svc.download_file(request, spaceType, departmentId, path, name, disposition, current_user)


@router.post("/download-zip")
async def download_zip(request: Request, payload: DeleteRequest, current_user: dict = Depends(get_current_user)):
    # 传 dict 给 service，内部使用 payload.get
    return await download_svc.download_zip(request, payload.dict(), current_user)


@router.get('/pack')
async def pack_download_dir(
    request: Request,
    spaceType: Optional[str] = None,
    departmentId: Optional[str] = None,
    path: str = '',
    name: Optional[str] = None,
    pack: int = 0,
    current_user: dict = Depends(get_current_user),
):
    return await pack_svc.pack_download_dir(request, spaceType, departmentId, path, name, pack, current_user)


@router.post('/pack')
async def pack_download_multi(body: PackRequest, current_user: dict = Depends(get_current_user)):
    return await pack_svc.pack_download_multi(body, current_user)


@router.post('/pack-temp', response_model=PackTempResponse)
async def pack_to_temp(body: PackTempRequest, current_user: dict = Depends(get_current_user)):
    return await pack_svc.pack_to_temp(body.dict(), current_user)


@router.post('/pack-async')
async def pack_async(body: PackTempRequest, current_user: dict = Depends(get_current_user)):
    """创建异步打包任务，返回 jobId。"""
    job_id = pack_async_svc.create_job(body.dict(), current_user)
    return {"jobId": job_id}


@router.get('/pack-status')
async def pack_status(jobId: str, current_user: dict = Depends(get_current_user)):
    job = pack_async_svc.get_job(jobId)
    if not job:
        raise HTTPException(status_code=404, detail="任务未找到")
    # 简单的权限检查：仅允许任务所有者或 super/op 查看（可根据需要放宽）
    owner = job.get('owner')
    role = current_user.get('role')
    if owner and role not in ('super', 'op') and owner != (current_user.get('phone') or current_user.get('name')):
        raise HTTPException(status_code=403, detail='无权限查看该任务')
    # 返回任务简要信息
    return {
        'id': job.get('id'),
        'status': job.get('status'),
        'result': job.get('result'),
        'error': job.get('error'),
        'created_at': job.get('created_at'),
        'updated_at': job.get('updated_at'),
    }


@router.post('/move')
async def move_items(payload: MoveRequest, current_user: dict = Depends(get_current_user)):
    # 注意：个人保险库(safe)到其他空间的移动/复制在 services 层已有严格权限控制，
    # 前端若收到 403/400 应提示用户，无须在此处静默吞掉异常。
    # 传 dict 给 service，内部使用 payload.get 访问字段
    return await ops_svc.move_items(payload.dict(), current_user)


@router.post('/copy')
async def copy_items(request: Request, payload: CopyRequest, current_user: dict = Depends(get_current_user)):
    # 注意：个人保险库(safe)到其他空间的移动/复制在 services 层已有严格权限控制，
    # 前端若收到 403/400 应提示用户，无须在此处静默吞掉异常。
    # 传 dict 给 service，内部使用 payload.get 访问字段
    client_ip = request.client.host if request.client else ""
    return await ops_svc.copy_items(payload.dict(), current_user, client_ip)


@router.delete("")
async def delete_items(request: Request, payload: DeleteRequest, current_user: dict = Depends(get_current_user)):
    # 传 dict 给 service，内部用 payload.get 访问
    return await ops_svc.delete_items(request, payload.dict(), current_user)


@router.put("/rename")
async def rename_item(request: Request, payload: RenameRequest, current_user: dict = Depends(get_current_user)):
    return await ops_svc.rename_item(request, payload.dict(), current_user)


@router.get("/search", response_model=List[SearchItem])
async def search_items(
    request: Request,
    spaceType: str = Query(..., description="空间类型:public / department / safe"),
    departmentId: Optional[str] = Query(None, description="部门空间时的部门 ID"),
    path: str = Query("", description="起始路径，相对于空间根目录"),
    keyword: str = Query("", description="名称关键词（包含匹配）"),
    current_user: dict = Depends(get_current_user),
):
    """搜索委托给 service，结果为 dict 列表，由 FastAPI 根据 response_model 转换为 SearchItem。"""
    client_ip = request.client.host if request.client else ""
    return await search_zip_svc.search_items(spaceType, departmentId, path, keyword, current_user, client_ip)


@router.post("/unzip")
async def unzip_file(request: Request, payload: UnzipRequest, current_user: dict = Depends(get_current_user)):
    """调用抽取到service层的解压逻辑，保持与legacy行为一致。"""
    client_ip = request.client.host if request.client else ""
    return await search_zip_svc.unzip_file(payload.dict(), current_user, client_ip)


@router.post("/compress")
async def compress_items(request: Request, payload: CompressRequest, current_user: dict = Depends(get_current_user)):
    """调用抽取到service层的压缩逻辑，保持与legacy行为一致。"""
    client_ip = request.client.host if request.client else ""
    return await search_zip_svc.compress_items(payload.dict(), current_user, client_ip)


@router.get("/recycle/list", response_model=RecycleListResponse)
async def list_recycle_items(
    scope: Optional[str] = Query(None),
    spaceType: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    return await recycle_svc.list_recycle_items(scope, spaceType, keyword, page, pageSize, current_user)


@router.post("/recycle/restore")
async def restore_recycle_items(payload: RecycleIdsRequest, current_user: dict = Depends(get_current_user)):
    return await recycle_svc.restore_recycle_items(payload.dict(), current_user)


@router.post("/recycle/purge")
async def purge_recycle_items(payload: RecycleIdsRequest, current_user: dict = Depends(get_current_user)):
    return await recycle_svc.purge_recycle_items(payload.dict(), current_user)


@router.post("/recycle/empty")
async def empty_recycle(current_user: dict = Depends(get_current_user)):
    return await recycle_svc.empty_recycle(current_user)


@router.get("/favorites", response_model=List[FavoriteItem])
async def list_favorite_paths(current_user: dict = Depends(get_current_user)):
    phone = current_user.get("phone") or ""
    return favorites_svc.list_favorites(phone)


@router.post("/favorites", response_model=FavoriteItem)
async def add_favorite_path(item: FavoriteItem, current_user: dict = Depends(get_current_user)):
    phone = current_user.get("phone") or ""
    data = favorites_svc.add_favorite(
        phone,
        item.spaceType,
        item.departmentId,
        item.path or "",
        item.displayName,
    )
    # FastAPI 会根据 FavoriteItem 进行转换
    return data


class FavoriteDeleteRequest(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str


@router.delete("/favorites")
async def delete_favorite_path(payload: FavoriteDeleteRequest, current_user: dict = Depends(get_current_user)):
    phone = current_user.get("phone") or ""
    favorites_svc.remove_favorite(phone, payload.spaceType, payload.departmentId, payload.path or "")
    return {"ok": True}

