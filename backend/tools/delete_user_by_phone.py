from pathlib import Path
import sqlite3
import sys
from backend.services.files import favorites as favorites_svc

# 脚本位置：backend/tools/delete_user_by_phone.py
# 数据库路径：项目根 data/users.db
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / 'data'
DB_PATH = DATA_ROOT / 'users.db'


def delete_user(phone: str):
    if not DB_PATH.exists():
        print(f'数据库不存在: {DB_PATH}')
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM users WHERE phone = ?', (phone,))
        conn.commit()
        if cur.rowcount:
            print(f'已删除手机号为 {phone} 的账号。')
            # 联动删除收藏路径记录
            try:
                favorites_svc.remove_by_user(phone)
            except Exception:
                # 不影响主流程
                pass
        else:
            print(f'未找到手机号为 {phone} 的账号（无需删除）。')
    finally:
        conn.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python backend/tools/delete_user_by_phone.py 13800000001')
        sys.exit(1)
    phone_arg = sys.argv[1].strip()
    if not phone_arg:
        print('错误：手机号不能为空。')
        sys.exit(1)
    delete_user(phone_arg)
