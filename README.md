# 视频上传平台

全栈视频上传平台，支持 TB 级大文件分片上传、断点续传、角色权限控制。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12 + FastAPI + SQLAlchemy (async) |
| 数据库 | PostgreSQL 16 |
| 存储 | 阿里云 OSS (oss2 SDK) |
| 前端 | Vue 3 + Vite + Pinia + Element Plus |
| 部署 | Docker + docker-compose |
| CI/CD | GitHub Actions |

---

## 快速开始（本地开发）

### 前置条件

- Docker Desktop
- 阿里云 OSS AccessKey（已提供）

### 1. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入：

```env
OSS_ACCESS_KEY_ID=<你的 AccessKey ID>
OSS_ACCESS_KEY_SECRET=<你的 AccessKey Secret>
OSS_BUCKET_NAME=platform-eng-1
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com   # 本地开发用公网端点
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
```

> **注意**：运行在阿里云 ECS 内网时，将 `OSS_ENDPOINT` 改为
> `OSS_INTERNAL_ENDPOINT=oss-cn-hangzhou-internal.aliyuncs.com`
> 以避免公网流量费用。

### 2. 启动服务

```bash
docker-compose up --build
```

| 服务 | 地址 |
|---|---|
| 前端 | http://localhost |
| 后端 API | http://localhost:8000 |
| API 文档（开发模式）| http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |
| Prometheus 指标 | http://localhost:8000/metrics |

### 3. 本地前端开发（热更新）

```bash
cd frontend
npm install
npm run dev
```

前端 dev server（5173 端口）通过 Vite proxy 将 `/api/*` 转发到后端 8000 端口。

---

## 部署到 ECS

```bash
# 1. SSH 登录 ECS
ssh root@xxx.xxx.xxx.xxx

# 2. 安装 Docker
curl -fsSL https://get.docker.com | sh
apt install docker-compose-plugin -y

# 3. 克隆仓库
git clone <repo_url> && cd video-platform

# 4. 配置 .env（同上）
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入凭证

# 5. 生产启动（无热重载卷挂载）
docker-compose -f docker-compose.yml up -d --build
```

---

## 架构概述

```
┌─────────────┐    HTTP     ┌──────────────────────────────────────────────┐
│  Vue 3 SPA  │────/api/───▶│  Nginx reverse proxy (port 80)               │
│  (Element+) │             └──────────────┬───────────────────────────────┘
└─────────────┘                            │ proxy_pass
                                           ▼
                              ┌────────────────────────┐
                              │  FastAPI (port 8000)   │
                              │  ├─ /auth/*            │
                              │  ├─ /videos/*          │
                              │  ├─ /videos/upload/*   │
                              │  └─ /admin/*           │
                              └────────┬───────────────┘
                                       │
                     ┌─────────────────┼──────────────────┐
                     ▼                 ▼                   ▼
             ┌──────────────┐  ┌────────────┐  ┌──────────────────┐
             │  PostgreSQL  │  │  OSS2 SDK  │  │  Thread pool     │
             │  (metadata)  │  │  (sync→    │  │  executor        │
             │              │  │   async)   │  │  (32 workers)    │
             └──────────────┘  └────────────┘  └──────────────────┘
                                       │
                              ┌────────────────────┐
                              │  阿里云 OSS Bucket  │
                              │  (Hangzhou/HK)      │
                              └────────────────────┘
```

---

## 分片上传流程

```
客户端                              服务端                    阿里云 OSS
  │                                   │                          │
  │─── POST /videos/upload/init ──────▶│                          │
  │       (filename, size, type)       │── init_multipart_upload ─▶│
  │                                   │◀─── oss_upload_id ────────│
  │◀─── session_id, total_chunks ─────│                          │
  │     chunk_size, uploaded_chunks   │                          │
  │                                   │                          │
  │─── PUT /upload/:id/chunk?n=1 ─────▶│                          │
  │     (raw bytes, octet-stream)      │── upload_part(n, data) ──▶│
  │                                   │◀─── ETag ─────────────────│
  │◀─── {progress: 1.0%} ─────────────│    (stored in DB)        │
  │                                   │                          │
  │  [并发3个分片，失败自动指数退避重试]  │                          │
  │                                   │                          │
  │─── POST /upload/:id/complete ─────▶│                          │
  │                                   │── complete_multipart ────▶│
  │◀─── {status: "processing"} ───────│    ([{PartNumber, ETag}]) │
  │                                   │                          │
```

**断点续传**：`init` 返回 `uploaded_chunks: [1,2,5,...]`，客户端跳过已上传分片，直接续传剩余部分。

**分片大小自适应**：
- 默认 10 MB/片
- 当文件 > 90 GB 时，自动调大分片确保总分片数 ≤ 9000（OSS 上限 10000）
- 客户端可通过 `chunk_size` 参数自定义

---

## API 概览

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | /auth/register | 公开 | 注册 |
| POST | /auth/login | 公开 | 登录，返回 JWT |
| POST | /auth/logout | Token | 退出 |
| GET | /videos | Token | 视频列表（按角色过滤） |
| GET | /videos/:id | Token | 视频详情 + 预签名播放 URL |
| DELETE | /videos/:id | 上传者+/管理员 | 软删除 |
| POST | /videos/upload/init | 上传者+ | 初始化分片上传 |
| PUT | /videos/upload/:id/chunk | 上传者+ | 上传单个分片 |
| POST | /videos/upload/:id/complete | 上传者+ | 完成上传 |
| DELETE | /videos/upload/:id/abort | 上传者+ | 取消并清理 |
| GET | /admin/users | 管理员 | 用户列表 |
| PATCH | /admin/users/:id/role | 管理员 | 修改角色 |
| GET | /health | 公开 | 健康检查 |
| GET | /metrics | 公开 | Prometheus 指标 |

完整文档：启动后访问 `http://localhost:8000/docs`（需 `DEBUG=true`）

---

## 已实现功能

### 必须实现
- [x] AU-01 邮箱+密码注册（bcrypt 加密）
- [x] AU-02 JWT 登录，含过期时间
- [x] AU-04 受保护路由，Token 缺失返回 401
- [x] UP-01 上传视频至 OSS（MP4/MOV/AVI/MKV）
- [x] UP-02 分片/分块上传（TB 级支持，自动调整分片大小）
- [x] UP-03 断点续传（init 返回已上传分片列表）
- [x] UP-04 客户端实时进度（百分比 + 已上传分片数）
- [x] UP-05 分片失败自动重试（3 次，指数退避 + 随机抖动）
- [x] UP-06 上传前文件格式校验（扩展名 + MIME 类型）
- [x] ST-01 PostgreSQL 存储视频元数据
- [x] 角色权限（viewer/uploader/admin）
- [x] 完整 API 端点

### 加分项
- [x] AU-03 注册时选择角色；管理员可修改角色
- [x] UP-07 并发分片上传（默认 3 个并发，可配置）
- [x] UP-08 取消上传（中止 OSS 分片上传，清理临时数据）
- [x] ST-03 软删除（标记 is_deleted，不立即删除 OSS 对象）
- [x] ST-04 按用户统计存储用量（storage_used 字段，原子更新）
- [x] 4.1 Vue 3 前端（Element Plus，拖拽上传，进度条，管理后台）
- [x] 4.2 客户端分片大小可配置；带抖动指数退避
- [x] 4.3 结构化 JSON 日志（structlog）；/health；Docker + docker-compose；GitHub Actions CI
- [x] 4.3 Prometheus 指标（/metrics：请求数、延迟）
- [x] 4.4 CORS 配置；输入校验（Pydantic）；OSS 预签名 URL 播放；/auth 限流（slowapi）

---

## 设计决策与权衡

### 1. 服务端代理 vs 客户端直传 OSS

当前实现：分片数据经由 FastAPI → OSS（服务端代理）。

- **优点**：服务端可精确控制权限、记录进度、统一错误处理；不暴露 OSS 凭证给客户端。
- **缺点**：对于 TB 级文件，服务端带宽成为瓶颈；ECS 到 OSS 内网传输是免费的（本实现中使用内网端点缓解）。

**生产优化方案**：`init` 时为每个分片生成带签名的 OSS 预签名 PUT URL，客户端直传 OSS，服务端只记录 ETag。可通过配置开关切换。

### 2. 同步 oss2 库的异步化

oss2 是同步库，通过 `asyncio.get_event_loop().run_in_executor(dedicated_thread_pool)` 包装，避免阻塞 FastAPI event loop。线程池大小为 32，可通过环境变量调整。

### 3. 视频状态流转

`uploading → processing → ready` —— `processing` 状态预留给后续转码/缩略图生成（后台任务队列，未在本版本实现）。

### 4. JWT 无状态登出

当前登出仅清除客户端 Token（无服务端撤销）。如需严格撤销，可将 JWT `jti` 存入 Redis 黑名单（代码注释中已标注扩展点）。

### 5. 数据库表设计

`upload_chunks` 表的 `ON DELETE CASCADE` 确保 session 删除时 chunk 记录自动清理。`storage_used` 在同一事务内更新，避免最终一致性漂移。

---

## 已知限制

