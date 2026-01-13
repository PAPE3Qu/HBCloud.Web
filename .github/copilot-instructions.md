# Copilot Instructions for HBCloud.Web

目的：给 AI 编码代理快速上手本仓库的最小可执行说明，包含架构、运行命令、关键约定与常改动位置。

## 1) 大体架构（一眼要点）
- **前端**：[frontend/](frontend/) — Vue 3 + Vite + Composition API。页面在 [frontend/src/views](frontend/src/views/)（如 `FileBrowser.vue`），HTTP 客户端封装在 [frontend/src/services](frontend/src/services/)（示例：`recycle.js`, `share.js`）。使用 axios 发送请求，JWT 存储在 localStorage。
- **后端**：[backend/](backend/) — FastAPI（入口: `backend/main.py`），路由在 [backend/routers/](backend/routers/)（如 `files.py`, `auth.py`, `users.py`），业务逻辑在 [backend/services/](backend/services/)（特别是 `files/` 子目录）。使用 pydantic 模型，JWT 认证。
- **数据与文件**：多 SQLite 数据库 + 文件系统存储。
  - 数据库：`data/users.db`（用户/角色/收藏）、`data/recycle_bin.db`（回收站）、`data/audit_index/file_detail.db`（文件统计）。
  - 文件存储：`data/public/`（公共）、`data/departments/<dept>/`（部门）、`data/safe/<phone>/`（个人保险库）、`data/recycle/`（回收文件）。
  - 临时：`data/tmp_packs/pack_jobs/`（异步打包任务 JSON）、`data/tmp_big_uploads/`、`data/tmp-uploads/`。

## 2) 运行与常用命令（可直接复制运行）
- **后端（开发）**：
  - 安装依赖：`pip install -r backend/requirements.txt`
  - 运行服务：`uvicorn backend.main:app --reload --host 127.0.0.1 --port 8083`
  - 日志：文本日志在 `data/log/yyyy-mm-dd.log`，审计 JSON 在 `data/audit_index/`。
- **前端（开发）**：
  - 安装依赖：在 `frontend/` 运行 `npm install`
  - 启动：`npm run dev`（Vite 服务器在 5173，代理 `/api` 到后端 8083）
- **构建前端**：`npm run build`（输出到 `frontend/dist/`）

## 3) 项目特定约定（必须遵守）
- **路由前缀**：`backend/main.py` 挂载 `/api/files`（文件）、`/api/auth`（认证）、`/api/users`（用户管理）、`/api`（分享链接）。修改时保持一致。
- **业务分层**：路由层（`backend/routers/*.py`）仅参数校验与响应包装，核心逻辑在 `backend/services/`（如 `backend/services/files/recycle.py` 处理回收逻辑）。
- **回收策略**：删除先移动文件到 `data/recycle/` 并写 `recycle_bin.db`，物理删除需单独脚本；参考 `backend/services/files/recycle.py`。
- **密码与认证**：使用 `pbkdf2_sha256` 哈希（见 `backend/routers/auth.py`），JWT 过期检查。
- **空间类型**：`public`（公共）、`department`（部门，需 `departmentId`）、`safe`（个人保险库，按手机号隔离）。
- **部门配置**：`data/departments/<id>/config.json` 定义权限；逻辑在 `backend/services/files/dept_roles.py`。
- **异步打包**：大文件打包用 JSON 任务存储（`tmp_packs/pack_jobs/`），并发限制 2；见 `backend/services/files/pack_async.py`。
- **日志与审计**：`write_log()` 写文本日志，`append_audit_record()` 写结构化审计；关键操作前后调用。

## 4) 常见改动点与示例文件
- **文件操作**：`backend/routers/files.py` + `backend/services/files/*`（如 `upload.py` 分片上传，`pack.py` 同步打包）。
- **用户管理**：`backend/routers/users.py` + 数据库 `users.db`。
- **前端页面**：`frontend/src/views/FileBrowser.vue`（文件浏览主页面，使用 Composition API）。
- **工具脚本**：`backend/tools/`（如 `import_users_from_csv.py` 批量导入用户）。
- **配置**：`backend/config.py`（路径、环境变量如 `HBCLOUD_PACK_MAX_BYTES`）。

## 5) 调试与定位问题
- 无单元测试；调试靠启动服务，观察 `data/log/` 日志和 SQLite 数据库（用 `sqlite3 data/users.db` 查询）。
- 前端代理到后端，确保端口匹配（Vite 5173 → 后端 8083）。
- 错误栈：FastAPI 自动返回 JSON 错误；前端 axios 拦截器处理。
- 打包调试：检查 `tmp_packs/pack_jobs/` JSON 任务状态。

## 6) 安全与不可改约束（显著提示）
- 不要删 `data/`：包含用户文件和数据库，直接删除丢失数据；修改走回收/迁移。
- 密码盐：`backend/config.py` 的 `PASSWORD_SALT`，生产环境替换。
- 权限检查：`ensure_department_read_access()` 等函数确保空间访问控制。

## 7) 贡献建议给 AI
- 优先在 `backend/services/` 实现逻辑，再在 `backend/routers/` 加校验。示例：新增收藏 → `services/files/favorites.py` + `routers/files.py`。
- 修改 DB：更新服务层 CRUD 和初始化函数（如 `main.py` 的 `_init_users_db()`）。
- 前端：用 Vue 3 Composition API，axios 请求封装在 `services/`。
- 新功能：参考现有模式，如异步任务用 JSON 文件存储状态。