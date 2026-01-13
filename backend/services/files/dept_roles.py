import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from time import time

from ...config import DATA_ROOT

USERS_DB = DATA_ROOT / 'users.db'


def _get_conn() -> sqlite3.Connection:
  conn = sqlite3.connect(USERS_DB)
  conn.row_factory = sqlite3.Row
  return conn


def get_dept_roles(dept_id: str) -> Dict[str, List[Dict[str, Any]]]:
  """返回指定部门的角色列表，按 dept / member 分组，附带用户姓名和手机号。"""
  if not dept_id:
    return {"dept": [], "member": []}

  conn = _get_conn()
  try:
    cur = conn.cursor()
    cur.execute(
      """
      SELECT r.phone, r.role, u.name
      FROM dept_roles r
      LEFT JOIN users u ON u.phone = r.phone
      WHERE r.dept_id = ?
      ORDER BY r.id ASC
      """,
      (dept_id,),
    )
    dept_list: List[Dict[str, Any]] = []
    member_list: List[Dict[str, Any]] = []
    for row in cur.fetchall():
      item = {
        "phone": row["phone"],
        "name": row["name"] or row["phone"],
      }
      if row["role"] == "dept":
        dept_list.append(item)
      elif row["role"] == "member":
        member_list.append(item)
    return {"dept": dept_list, "member": member_list}
  finally:
    conn.close()


def set_dept_roles(dept_id: str, admins: List[str], members: List[str], updated_by: Optional[str] = None) -> Dict[str, Any]:
  """覆盖指定部门的部门管理员 / 部门成员列表。

  - admins: 部门管理员手机号列表
  - members: 部门成员手机号列表
  """
  if not dept_id:
    raise ValueError("dept_id is required")

  admins = [p.strip() for p in admins or [] if p and p.strip()]
  members = [p.strip() for p in members or [] if p and p.strip()]

  now = float(time())
  conn = _get_conn()
  try:
    cur = conn.cursor()
    # 先查询旧值用于返回和审计
    cur.execute("SELECT phone, role FROM dept_roles WHERE dept_id = ?", (dept_id,))
    before_rows = cur.fetchall()
    before = {
      "dept": [r["phone"] for r in before_rows if r["role"] == "dept"],
      "member": [r["phone"] for r in before_rows if r["role"] == "member"],
    }

    # 全量覆盖策略：删除该部门所有记录后重建
    cur.execute("DELETE FROM dept_roles WHERE dept_id = ?", (dept_id,))

    # 插入新的管理员
    for phone in admins:
      cur.execute(
        """
        INSERT INTO dept_roles (dept_id, phone, role, created_at, updated_at)
        VALUES (?, ?, 'dept', ?, ?)
        """,
        (dept_id, phone, now, now),
      )

    # 插入新的成员
    for phone in members:
      cur.execute(
        """
        INSERT INTO dept_roles (dept_id, phone, role, created_at, updated_at)
        VALUES (?, ?, 'member', ?, ?)
        """,
        (dept_id, phone, now, now),
      )

    conn.commit()

    after = {
      "dept": admins,
      "member": members,
    }

    return {"before": before, "after": after}
  finally:
    conn.close()


def get_user_dept_role(phone: str, dept_id: str) -> Optional[str]:
  """查询用户在某部门内的角色：返回 'dept' / 'member' / None。"""
  phone = (phone or "").strip()
  if not phone or not dept_id:
    return None
  conn = _get_conn()
  try:
    cur = conn.cursor()
    cur.execute(
      "SELECT role FROM dept_roles WHERE dept_id = ? AND phone = ? ORDER BY id ASC LIMIT 1",
      (dept_id, phone),
    )
    row = cur.fetchone()
    if not row:
      return None
    return row["role"]
  finally:
    conn.close()


def delete_dept_roles(dept_id: str) -> int:
  """删除指定部门的所有角色绑定记录。返回删除行数。"""
  dept_id = (dept_id or '').strip()
  if not dept_id:
    return 0
  conn = _get_conn()
  try:
    cur = conn.cursor()
    cur.execute("DELETE FROM dept_roles WHERE dept_id = ?", (dept_id,))
    conn.commit()
    return int(cur.rowcount or 0)
  finally:
    conn.close()
