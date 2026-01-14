# HBCloud.Web 开发者文档

本文件面向开发与维护人员，说明项目结构、运行方式、关键约定与常见调试点。

## 目录结构

- backend：FastAPI 后端
- frontend：Vue 3 + Vite 前端
- data：运行时数据（文件与 SQLite 数据库）
- 项目引导：面向使用者的业务说明文档与示例数据

## 技术栈

- 前端：Vue 3（Composition API）+ Vite + Axios
- 后端：FastAPI + Uvicorn
- 鉴权：JWT（前端 localStorage 保存 token；后端校验 exp 过期）
- 存储：文件系统为主，SQLite 作为辅助索引/记录

## 本地开发启动

### 后端

在项目根目录执行：

```bash
pip install -r backend/requirements.txt
uvicorn backend.__init__:app --reload --host 127.0.0.1 --port 8083
```

后端入口与路由挂载见 backend/main.py：

- /api/files：文件与空间相关接口
- /api/auth：登录、注册、改密
- /api/users：用户管理
- /api/share：分享短码
- /api/audit：审计
- /api/shortcut：快捷入口相关

### 前端

在 frontend 目录执行：

```bash
npm install
npm run dev
```

开发代理见 frontend/vite.config.js：

- 前端 dev server：127.0.0.1:5173
- /api 代理到后端：127.0.0.1:8083

构建：

```bash
npm run build
```

## 关键数据目录与数据库

重要：不要在开发/部署中随意删除 data 目录。

- 文件存储
  - data/public：公共空间
  - data/departments/<departmentId>：部门空间
  - data/safe/<phone>：个人保险库
  - data/recycle：回收站物理目录
- 临时目录
  - data/tmp_packs/pack_jobs：异步打包任务 JSON
  - data/tmp_big_uploads：大文件分片临时目录
  - data/tmp-uploads：上传临时目录
- SQLite（位置与用途）
  - data/users.db：用户/角色/部门权限/快捷访问等
  - data/recycle_bin.db：回收站记录
  - data/audit_index/file_detail.db：文件统计索引

## 前端代码导航

- 文件浏览主页面：frontend/src/views/FileBrowser.vue
  - 空间/路径切换、面包屑导航、上传/移动/复制/打包下载等交互均在此页面
  - 近期做了面包屑与右侧按钮区的“碰撞处理”与响应式紧凑模式
- 回收站：frontend/src/views/RecycleBin.vue
- 分享/短码解析：frontend/src/services/share.js

## 后端代码导航

后端遵循“路由层只做参数校验与响应包装，核心逻辑在 services”原则。

- 路由
  - backend/routers/files.py：文件/空间相关 API
  - backend/routers/auth.py：认证
  - backend/routers/users.py：用户管理
  - backend/routers/share_links.py：分享短码
  - backend/routers/audit.py：审计
- 服务层（文件相关）
  - backend/services/files/upload.py：上传（含分片/大文件）
  - backend/services/files/download.py：下载与计数
  - backend/services/files/recycle.py：回收站策略
  - backend/services/files/pack_async.py：异步打包任务
  - backend/services/files/links.py：快捷链接
  - backend/services/files/favorites.py：快速访问（收藏）

## 约定与注意事项

- 路由前缀
  - 文件相关统一在 /api/files 下
- 回收策略
  - 删除默认进入回收站目录并写 recycle_bin.db；物理删除需走回收站“彻底删除”或维护脚本
- 个人保险库 safe
  - 普通用户仅能访问自己的手机号目录；前端展示路径与后端 path 参数存在差异，相关转换在 FileBrowser.vue 内
- 异步打包
  - 任务落盘为 JSON（data/tmp_packs/pack_jobs），前端通过 /api/files/pack-status 轮询

## 常见调试点

- 打包下载卡住/失败
  - 检查 data/tmp_packs/pack_jobs 中任务状态与错误字段
  - 查看后端日志 data/log 下当日日志
- 权限问题（403）
  - department 空间是否选择了部门
  - 部门 config.json 与 dept_roles 配置是否正确
- safe 空间路径不对
  - 确认当前用户 phone 与超管角色；检查 FileBrowser.vue 的 safe 路径转换逻辑
