import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# 数据根目录改为项目根目录下的 data 目录，便于备份与管理
DATA_DIR = PROJECT_ROOT / "data"  # 新增：与历史版本兼容的别名
DATA_ROOT = DATA_DIR
PUBLIC_ROOT = DATA_ROOT / "public"
DEPT_ROOT = DATA_ROOT / "departments"
RECYCLE_ROOT = DATA_ROOT / ".recycle"
SAFE_ROOT = DATA_ROOT / "safe"  # 个人保险库根目录

# 管理员邀请码与超级管理员账号配置
ADMIN_INVITE_CODE = os.getenv("HBCLOUD_ADMIN_INVITE", "335915")
SUPER_ADMIN_USERNAME = os.getenv("HBCLOUD_SUPER_ADMIN", "admin")
SUPER_ADMIN_PASSWORD = os.getenv("HBCLOUD_SUPER_ADMIN_PWD", "123456")

# 简单演示用：密码加密盐（真实环境请替换为更安全的方案）
PASSWORD_SALT = os.getenv("HBCLOUD_PWD_SALT", "hbcloud-demo-salt")

# 确保目录存在
for p in [DATA_ROOT, PUBLIC_ROOT, DEPT_ROOT, RECYCLE_ROOT, SAFE_ROOT]:
    os.makedirs(p, exist_ok=True)


class SpaceType:
    PUBLIC = "public"
    DEPARTMENT = "department"
    SAFE = "safe"  # 个人保险库空间


VALID_SPACE_TYPES = {SpaceType.PUBLIC, SpaceType.DEPARTMENT, SpaceType.SAFE}

# 打包下载的默认最大允许大小（字节），可通过环境变量 HBCLOUD_PACK_MAX_BYTES 覆盖
PACK_MAX_SIZE_BYTES = int(os.getenv("HBCLOUD_PACK_MAX_BYTES", str(1024 * 1024 * 1024)))
