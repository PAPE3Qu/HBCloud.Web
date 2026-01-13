from fastapi import APIRouter, Depends, HTTPException
import json
from typing import List, Dict, Any
import sqlite3  # 新增：用于捕获 sqlite3.OperationalError
from pathlib import Path

from ..config import DATA_ROOT, SAFE_ROOT
from .auth import get_current_user, _get_db_conn
from ..services.files.base import write_log  # 新增：复用文件服务里的文本日志工具
from .audit import append_audit_record, AuditRecord  # 新增：结构化审计日志

router = APIRouter()

@router.get("/", response_model=List[dict])
def list_users(current_user: dict = Depends(get_current_user)):
    # 仅要求已登录即可（用于空间权限成员选择弹窗展示全量已注册用户）
    if not current_user:
        raise HTTPException(status_code=401, detail="not_authenticated")

    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT phone, name, role, is_active FROM users ORDER BY id ASC"
        )
        rows = cur.fetchall()
        clean = []
        for row in rows:
            clean.append({
                "phone": row["phone"],
                "name": row["name"],
                "role": row["role"],
                "is_active": bool(row["is_active"]),
            })
        return clean
    finally:
        conn.close()

@router.put("/op-set")
def set_op_users(payload: dict, current_user: dict = Depends(get_current_user)):
    """维护系统管理员(op)名单：仅 super 可操作。

    payload: { phones: string[] }
    - phones 表示最终应为 op 的手机号集合
    - 禁止修改任何 super 用户
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="not_authenticated")
    if (current_user.get("role") or "").lower() != "super":
        raise HTTPException(status_code=403, detail="forbidden")

    phones = payload.get("phones") or []
    if not isinstance(phones, list):
        raise HTTPException(status_code=400, detail="invalid_payload")

    # 规范化
    phone_set = set([str(p).strip() for p in phones if str(p).strip()])

    conn = _get_db_conn()
    try:
        cur = conn.cursor()

        # 取出所有用户（含当前角色）
        cur.execute("SELECT id, phone, role FROM users")
        rows = cur.fetchall()
        by_phone = {row["phone"]: row for row in rows}

        # 找出 super 用户（禁止修改）
        super_phones = set([row["phone"] for row in rows if (row["role"] or "").lower() == "super"])

        # 记录原始 op 名单，用于日志
        before_ops = sorted([row["phone"] for row in rows if (row["role"] or "").lower() == "op"])

        # changes
        to_op = []
        to_user = []

        for phone, row in by_phone.items():
            role = (row["role"] or "user").lower()
            if phone in super_phones:
                continue

            if phone in phone_set:
                # 设为 op
                if role != "op":
                    to_op.append(phone)
            else:
                # 不在名单里，若原为 op 则降级为 user
                if role == "op":
                    to_user.append(phone)

        # 执行更新（事务）
        if to_op:
            cur.executemany("UPDATE users SET role='op' WHERE phone=? AND role<>'super'", [(p,) for p in to_op])
        if to_user:
            cur.executemany("UPDATE users SET role='user' WHERE phone=? AND role<>'super'", [(p,) for p in to_user])
        conn.commit()

        # 变更后最新 op 名单，用于日志
        cur.execute("SELECT phone FROM users WHERE LOWER(role)='op' ORDER BY id ASC")
        op_rows_after = cur.fetchall()
        after_ops = sorted([r["phone"] for r in op_rows_after])

        # 写结构化审计日志
        from datetime import datetime
        now_ts = datetime.now().timestamp()
        editor_phone = (current_user.get("phone") or "").strip()

        # 注意：AuditRecord.spaceType 为必填字符串字段，这里无空间概念，用空字符串占位
        append_audit_record(
            AuditRecord(
                ts=now_ts,
                action="user_roles",
                path="/users/op-set",
                spaceType="",  # 修复：不能传 None
                departmentId=None,
                clientIp="",
                detail={
                    "scope": "system_ops",
                    "beforeOps": before_ops,
                    "afterOps": after_ops,
                    "toOp": sorted(to_op),
                    "toUser": sorted(to_user),
                    "updatedBy": editor_phone,
                },
            )
        )

        # 文本日志摘要一行，方便 grep
        write_log(
            "op_set before %s -> after %s toOp %s toUser %s updatedBy=%s"
            % (
                ",".join(before_ops),
                ",".join(after_ops),
                ",".join(sorted(to_op)),
                ",".join(sorted(to_user)),
                editor_phone,
            )
        )

        # 返回最新 users 列表（用于前端刷新表格/弹窗默认勾选）
        cur.execute("SELECT phone, name, role, is_active FROM users ORDER BY id ASC")
        rows2 = cur.fetchall()
        return [
            {
                "phone": r["phone"],
                "name": r["name"],
                "role": r["role"],
                "is_active": bool(r["is_active"]),
            }
            for r in rows2
        ]
    finally:
        conn.close()

@router.post("/disable/{phone}")
def disable_user(phone: str, current_user: dict = Depends(get_current_user)):
    """禁用账号（软删除）：设置 is_active=0。仅 super 可操作。同时清理其部门空间权限。"""
    if not current_user:
        raise HTTPException(status_code=401, detail="not_authenticated")
    if (current_user.get("role") or "").lower() != "super":
        raise HTTPException(status_code=403, detail="forbidden")

    phone = (phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="invalid_phone")

    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        # 不允许禁用 super 账号
        cur.execute("SELECT id, phone, role, is_active FROM users WHERE phone=?", (phone,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="user_not_found")
        if (row["role"] or "").lower() == "super":
            raise HTTPException(status_code=400, detail="cannot_disable_super")

        if not row["is_active"]:
            # 已是禁用状态，直接返回
            return {"phone": row["phone"], "disabled": True, "already": True}

        # 1. 先清理部门空间权限（若 dept_roles 表存在）
        removed_dept_roles = 0
        try:
            cur.execute(
                "DELETE FROM dept_roles WHERE phone=?",
                (phone,),
            )
            removed_dept_roles = cur.rowcount or 0
        except sqlite3.OperationalError:
            removed_dept_roles = 0

        # 2. 再禁用账号
        cur.execute("UPDATE users SET is_active=0 WHERE id=?", (row["id"],))
        conn.commit()

        # 审计
        from datetime import datetime
        now_ts = datetime.now().timestamp()
        editor_phone = (current_user.get("phone") or "").strip()
        append_audit_record(
            AuditRecord(
                ts=now_ts,
                action="user_disable",
                path=f"/users/disable/{phone}",
                spaceType="",
                departmentId=None,
                clientIp="",
                detail={
                    "phone": phone,
                    "removedDeptRoles": removed_dept_roles,
                    "updatedBy": editor_phone,
                },
            )
        )
        write_log(f"user_disabled phone={phone} removedDeptRoles={removed_dept_roles} by={editor_phone}")
        return {"phone": phone, "disabled": True, "already": False, "removedDeptRoles": removed_dept_roles}
    finally:
        conn.close()


@router.delete("/{phone}")
def hard_delete_user(phone: str, current_user: dict = Depends(get_current_user)):
    """硬删除账号：直接从 users 表移除，并清理其部门空间权限、重命名 safe 目录为 "{phone}__已禁用"。仅 super 可操作。"""
    if not current_user:
        raise HTTPException(status_code=401, detail="not_authenticated")
    if (current_user.get("role") or "").lower() != "super":
        raise HTTPException(status_code=403, detail="forbidden")

    phone = (phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="invalid_phone")

    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        # 先查出用户信息
        cur.execute("SELECT id, phone, role FROM users WHERE phone=?", (phone,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="user_not_found")
        if (row["role"] or "").lower() == "super":
            raise HTTPException(status_code=400, detail="cannot_delete_super")

        user_id = row["id"]

        # 1. 清理部门空间权限（dept_roles 表按 phone 删除记录）
        removed_dept_roles = 0
        try:
            cur.execute(
                "DELETE FROM dept_roles WHERE phone=?",
                (phone,),
            )
            removed_dept_roles = cur.rowcount or 0
        except sqlite3.OperationalError:
            # 没有该表则忽略
            removed_dept_roles = 0

        # 2. 删除账号记录
        cur.execute("DELETE FROM users WHERE id=?", (user_id,))
        deleted_rows = cur.rowcount or 0
        conn.commit()

        # 3. 处理 safe 目录重命名：data/safe/{phone} -> data/safe/{phone}__已禁用
        safe_dir = SAFE_ROOT / phone
        renamed_to = None
        try:
            if safe_dir.exists() and safe_dir.is_dir():
                target = SAFE_ROOT / f"{phone}__已禁用"
                safe_dir.rename(target)
                renamed_to = str(target)
        except Exception as e:
            # 仅记录日志，不中断删除流程
            write_log(f"user_hard_delete safe_rename_failed phone={phone} err={e}")

        # 审计与文本日志
        from datetime import datetime
        now_ts = datetime.now().timestamp()
        editor_phone = (current_user.get("phone") or "").strip()
        append_audit_record(
            AuditRecord(
                ts=now_ts,
                action="user_hard_delete",
                path=f"/users/{phone}",
                spaceType="",
                departmentId=None,
                clientIp="",
                detail={
                    "phone": phone,
                    "deletedRows": deleted_rows,
                    "removedDeptRoles": removed_dept_roles,
                    "safeRenamedTo": renamed_to,
                    "updatedBy": editor_phone,
                },
            )
        )
        write_log(
            f"user_hard_deleted phone={phone} deletedRows={deleted_rows} "
            f"removedDeptRoles={removed_dept_roles} safeRenamedTo={renamed_to} by={editor_phone}"
        )

        return {
            "phone": phone,
            "deleted": bool(deleted_rows),
            "removedDeptRoles": removed_dept_roles,
            "safeRenamedTo": renamed_to,
        }
    finally:
        conn.close()
