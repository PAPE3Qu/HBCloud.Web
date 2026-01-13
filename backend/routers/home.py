# 首页公告接口：/api/home/posts
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import json
import time
from ..config import DATA_ROOT
from .files import write_log
from .auth import get_current_user
from ..services.files.base import ensure_department_read_access, ensure_department_write_access

router = APIRouter(prefix="/api/home", tags=["home"]) 

DATA_PATH = Path(__file__).resolve().parents[1] / 'data' / 'home_posts.json'
DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

class Attachment(BaseModel):
    spaceType: str
    departmentId: Optional[str] = None
    path: str = ''
    name: str = ''
    is_dir: bool = False

class Post(BaseModel):
    id: str
    title: str
    content: str
    author: str = '匿名'
    departmentId: Optional[str] = None
    created_at: float
    attachments: List[Attachment] = []

class CreatePostRequest(BaseModel):
    title: str = ''
    content: str
    author: str = '匿名'
    departmentId: Optional[str] = None
    attachments: List[Attachment] = []

class PostListResponse(BaseModel):
    items: List[Post]
    total: int
    page: int
    pageSize: int


def _load_posts() -> List[dict]:
    if not DATA_PATH.exists():
        return []
    try:
        return json.loads(DATA_PATH.read_text(encoding='utf-8'))
    except Exception:
        return []


def _save_posts(items: List[dict]):
    DATA_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')


def _get_user_display_name(current_user: dict) -> str:
    return ((current_user or {}).get('name') or (current_user or {}).get('phone') or '').strip()


def _can_manage_post(post: dict, current_user: dict) -> bool:
    if (current_user or {}).get('role') == 'super':
        return True
    me = _get_user_display_name(current_user)
    if not me:
        return False
    author = (post.get('author') or '').strip()
    return bool(author and author == me)


def _post_is_visible_to_user(post: dict, current_user: dict) -> bool:
    """不带 departmentId 筛选时的可见性：
    - 公共动态（departmentId 为空）：所有登录用户可见；
    - 部门动态：需具备该部门读权限（关闭空间无权用户不可见）。
    """
    dept_id = (post.get('departmentId') or '').strip()
    if not dept_id:
        return True
    try:
        ensure_department_read_access(dept_id, current_user)
        return True
    except HTTPException:
        return False


@router.post('/posts', response_model=Post)
async def create_post(payload: CreatePostRequest, current_user: dict = Depends(get_current_user)):
    if not payload.author or not payload.author.strip():
        raise HTTPException(status_code=400, detail='发布者不能为空')

    # 部门动态：发布权限要求 dept/member 或 super/op
    if payload.departmentId:
        ensure_department_write_access(payload.departmentId, current_user)

    # 附件空间约束：公共动态只能挂公共空间附件；部门动态只能挂同部门附件
    for att in payload.attachments:
        if payload.departmentId:
            if att.spaceType != 'department' or (att.departmentId or '') != (payload.departmentId or ''):
                raise HTTPException(status_code=400, detail='部门动态仅允许选择当前部门空间内的附件')
        else:
            if att.spaceType != 'public':
                raise HTTPException(status_code=400, detail='公开动态仅允许选择公共空间附件')

    # 附件规则：最多5个文件 或 1个文件夹（不可混用）
    has_dir = any(att.is_dir for att in payload.attachments)
    files_count = sum(1 for att in payload.attachments if not att.is_dir)
    if has_dir:
        if len(payload.attachments) != 1 or files_count != 0:
            raise HTTPException(status_code=400, detail='附件规则：最多5个文件 或 1个文件夹（不可混用）')
    else:
        if files_count > 5:
            raise HTTPException(status_code=400, detail='最多选择5个文件作为附件')

    items = _load_posts()
    now = time.time()
    new_post = {
        'id': str(int(now * 1000)),
        'title': payload.title or '',
        'content': payload.content,
        'author': payload.author or '匿名',
        'departmentId': payload.departmentId,
        'created_at': now,
        'attachments': [att.dict() for att in payload.attachments],
    }
    items.insert(0, new_post)
    _save_posts(items)
    write_log(f"home_post_create id={new_post['id']} author={new_post['author']} dept={new_post['departmentId'] or ''}")
    return new_post


@router.delete('/posts/{post_id}')
async def delete_post(post_id: str, current_user: dict = Depends(get_current_user)):
    items = _load_posts()
    target = None
    for p in items:
        if str(p.get('id')) == str(post_id):
            target = p
            break
    if not target:
        raise HTTPException(status_code=404, detail='动态不存在或已删除')

    if not _can_manage_post(target, current_user):
        raise HTTPException(status_code=403, detail='无权删除该动态')

    items = [p for p in items if str(p.get('id')) != str(post_id)]
    _save_posts(items)
    deleter = _get_user_display_name(current_user)
    write_log(f"home_post_delete id={post_id} by={deleter}")
    return {"success": True}


@router.put('/posts/{post_id}', response_model=Post)
async def update_post(post_id: str, payload: CreatePostRequest, current_user: dict = Depends(get_current_user)):
    """编辑已有动态：覆盖标题、内容、作者、部门及附件。"""
    items = _load_posts()
    target = None
    for p in items:
        if str(p.get('id')) == str(post_id):
            target = p
            break
    if not target:
        raise HTTPException(status_code=404, detail='动态不存在或已删除')

    if not _can_manage_post(target, current_user):
        raise HTTPException(status_code=403, detail='无权编辑该动态')

    if not payload.author or not payload.author.strip():
        raise HTTPException(status_code=400, detail='发布者不能为空')

    # 部门动态：编辑权限要求 dept/member 或 super/op
    if payload.departmentId:
        ensure_department_write_access(payload.departmentId, current_user)

    # 附件空间约束
    for att in payload.attachments:
        if payload.departmentId:
            if att.spaceType != 'department' or (att.departmentId or '') != (payload.departmentId or ''):
                raise HTTPException(status_code=400, detail='部门动态仅允许选择当前部门空间内的附件')
        else:
            if att.spaceType != 'public':
                raise HTTPException(status_code=400, detail='公开动态仅允许选择公共空间附件')

    # 附件规则：最多5个文件 或 1个文件夹（不可混用）
    has_dir = any(att.is_dir for att in payload.attachments)
    files_count = sum(1 for att in payload.attachments if not att.is_dir)
    if has_dir:
        if len(payload.attachments) != 1 or files_count != 0:
            raise HTTPException(status_code=400, detail='附件规则：最多5个文件 或 1个文件夹（不可混用）')
    else:
        if files_count > 5:
            raise HTTPException(status_code=400, detail='最多选择5个文件作为附件')

    target['title'] = payload.title or ''
    target['content'] = payload.content
    target['author'] = payload.author or '匿名'
    target['departmentId'] = payload.departmentId
    target['attachments'] = [att.dict() for att in payload.attachments]
    _save_posts(items)
    write_log(f"home_post_update id={post_id} author={target['author']}")
    return target


@router.get('/posts', response_model=PostListResponse)
async def list_posts(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    departmentId: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    items = _load_posts()

    if departmentId:
        # 筛选部门：无权直接 403
        ensure_department_read_access(departmentId, current_user)
        items = [p for p in items if (p.get('departmentId') == departmentId)]
    else:
        # 全部模式：过滤无权访问的关闭部门动态
        items = [p for p in items if _post_is_visible_to_user(p, current_user)]

    total = len(items)
    start = (page - 1) * pageSize
    end = start + pageSize
    page_items = items[start:end]
    return PostListResponse(items=page_items, total=total, page=page, pageSize=pageSize)
