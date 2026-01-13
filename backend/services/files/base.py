from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import HTTPException

from ...config import PUBLIC_ROOT, DEPT_ROOT, SAFE_ROOT, SpaceType, VALID_SPACE_TYPES, DATA_ROOT

LOG_ROOT = DATA_ROOT / 'log'
LOG_ROOT.mkdir(parents=True, exist_ok=True)


def write_log(message: str) -> None:
    """写入一条简单的按日期分文件的日志记录到 data/log/yyyy-mm-dd.log。"""
    try:
        ts = datetime.now()
        fname = ts.strftime('%Y-%m-%d.log')
        path = LOG_ROOT / fname
        line = f"{ts.isoformat(timespec='seconds')} {message}\n"
        with path.open('a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        # 日志失败不影响主流程
        pass


def resolve_root(space_type: str, department_id: Optional[str], current_user: Dict[str, Any]) -> Path:
    """根据空间类型和当前用户解析物理根目录。"""
    if space_type not in VALID_SPACE_TYPES:
        raise HTTPException(status_code=400, detail="无效的空间类型")

    if space_type == SpaceType.PUBLIC:
        return PUBLIC_ROOT

    if space_type == SpaceType.DEPARTMENT:
        if not department_id:
            raise HTTPException(status_code=400, detail="部门空间需要提供 departmentId")
        return DEPT_ROOT / department_id

    if space_type == SpaceType.SAFE:
        # 超管可以浏览整个 /safe 目录
        if current_user.get("role") == "super":
            SAFE_ROOT.mkdir(parents=True, exist_ok=True)
            return SAFE_ROOT
        phone = (current_user.get("phone") or "").strip()
        if not phone:
            raise HTTPException(status_code=400, detail="当前用户缺少手机号信息，无法访问个人保险库")
        user_safe = SAFE_ROOT / phone
        user_safe.mkdir(parents=True, exist_ok=True)
        return user_safe

    raise HTTPException(status_code=400, detail="未知空间类型")


def ensure_department_read_access(dept_id: str, current_user: Dict) -> None:
    """部门空间读访问控制：列表 / 下载 / 搜索 / 打包等使用。

    规则：
    - super / op：始终允许；
    - 普通用户：
      - 若部门 isOpen 为 True，则允许（视同公共空间）；
      - 若 isOpen 为 False，则仅当其在该部门为 dept 或 member 时允许；
      - 否则 403。
    """
    from . import dept as dept_svc  # 局部导入以避免循环依赖
    from . import dept_roles as dept_roles_svc  # 局部导入

    dept_id = (dept_id or '').strip()
    if not dept_id:
        raise HTTPException(status_code=400, detail="缺少部门 ID")

    cfg = dept_svc.get_department_config(dept_id)
    is_open = bool(cfg.get('isOpen', True))

    role = current_user.get('role')
    phone = (current_user.get('phone') or '').strip()

    # 超级管理员 / 运维管理员：不受 isOpen 限制
    if role in ('super', 'op'):
        return

    # 部门角色
    dept_role = dept_roles_svc.get_user_dept_role(phone, dept_id)

    # 关闭空间：仅部门管理员 / 成员可访问
    if not is_open and dept_role not in ('dept', 'member'):
        raise HTTPException(status_code=403, detail="空间未开放或无访问权限")

    # 开放空间：任何登录用户可读
    return


def ensure_department_write_access(dept_id: str, current_user: Dict) -> None:
    """部门空间写操作控制：上传 / 删除 / 重命名 / 移动 / 复制 / 解压 / 压缩。

    规则：
    - super / op：始终允许；
    - 部门管理员（dept）/ 部门成员（member）：始终允许（不受 isOpen 影响）；
    - 其他角色：无论 isOpen 与否，一律 403。

    即：空间是否开放只决定“外部人是否可以访问该空间（读）”，
    部门内部成员与管理员的读写权限不受 isOpen 影响。
    """
    from . import dept_roles as dept_roles_svc  # 局部导入

    dept_id = (dept_id or '').strip()
    if not dept_id:
        raise HTTPException(status_code=400, detail="缺少部门 ID")

    role = current_user.get('role')
    phone = (current_user.get('phone') or '').strip()

    # 超级管理员 / 运维管理员拥有写权限
    if role in ('super', 'op'):
        return

    dept_role = dept_roles_svc.get_user_dept_role(phone, dept_id)
    if dept_role not in ('dept', 'member'):
        raise HTTPException(status_code=403, detail="空间未开放或无访问权限")

    return
