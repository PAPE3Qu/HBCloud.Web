from pathlib import Path
from typing import List, Dict, Any, Optional

from ...config import DATA_DIR

DB_PATH = DATA_DIR / "favorite_paths.db"


def _ensure_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS favorite_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_phone TEXT NOT NULL,
            space_type TEXT NOT NULL,
            department_id TEXT,
            path TEXT NOT NULL,
            display_name TEXT,
            UNIQUE(user_phone, space_type, department_id, path)
        )
        """
    )


def _get_conn():
    import sqlite3

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    _ensure_table(conn)
    return conn


def list_favorites(user_phone: str) -> List[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.execute(
            "SELECT id, space_type, department_id, path, display_name FROM favorite_paths WHERE user_phone = ? ORDER BY id ASC",
            (user_phone,),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "spaceType": r[1],
                "departmentId": r[2],
                "path": r[3],
                "displayName": r[4],
            }
            for r in rows
        ]
    finally:
        conn.close()


def add_favorite(user_phone: str, space_type: str, department_id: Optional[str], path: str, display_name: Optional[str] = None) -> Dict[str, Any]:
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO favorite_paths(user_phone, space_type, department_id, path, display_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_phone, space_type, department_id, path, display_name),
        )
        conn.commit()
        cur = conn.execute(
            "SELECT id, space_type, department_id, path, display_name FROM favorite_paths WHERE user_phone = ? AND space_type = ? AND IFNULL(department_id, '') = IFNULL(?, '') AND path = ?",
            (user_phone, space_type, department_id, path),
        )
        r = cur.fetchone()
        if not r:
            return {}
        return {
            "id": r[0],
            "spaceType": r[1],
            "departmentId": r[2],
            "path": r[3],
            "displayName": r[4],
        }
    finally:
        conn.close()


def remove_favorite(user_phone: str, space_type: str, department_id: Optional[str], path: str) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            "DELETE FROM favorite_paths WHERE user_phone = ? AND space_type = ? AND IFNULL(department_id, '') = IFNULL(?, '') AND path = ?",
            (user_phone, space_type, department_id, path),
        )
        conn.commit()
    finally:
        conn.close()


def remove_by_user(user_phone: str) -> None:
    """用于账号硬删除联动清理收藏记录。"""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM favorite_paths WHERE user_phone = ?", (user_phone,))
        conn.commit()
    finally:
        conn.close()
