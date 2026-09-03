# SmartGalleryAI 技术栈书

## 1. 总体原则

SmartGalleryAI 的后端技术栈以 Python 为核心，优先满足四个目标：

1. 本地优先：用户图片默认留在本机或私有服务器。
2. 可插拔 AI：OCR、图片描述、向量模型、云模型都可以替换。
3. 易部署：单机 SQLite 可以启动，进阶部署可切 PostgreSQL、Redis、Qdrant。
4. 开源友好：代码结构清晰，贡献者可以独立开发 Provider、索引器和 API。

## 2. 后端主栈

| 模块 | 选型 | 说明 |
| --- | --- | --- |
| Web 框架 | FastAPI | 类型提示友好，自带 OpenAPI，适合 AI 服务型后端。 |
| ASGI Server | Uvicorn | 本地开发和轻量部署足够成熟。 |
| 数据校验 | Pydantic v2 / pydantic-settings | 请求响应模型、环境变量配置。 |
| ORM | SQLAlchemy 2 | 适配 SQLite/PostgreSQL，社区稳定。 |
| 迁移 | Alembic | 后续正式管理数据库版本。 |
| 任务队列 | Celery | 处理批量导入、OCR、缩略图、向量化等耗时任务。 |
| Broker | Redis | 简单、成熟，Celery 默认生态好。 |
| 图片处理 | Pillow | 读取尺寸、格式、缩略图、基础转换。 |
| CLI | Typer | 后续提供 scan、reindex、worker 等命令。 |
| 测试 | pytest | Python 后端标准测试工具。 |
| 代码质量 | Ruff / mypy | 快速 lint、格式检查和类型检查。 |

## 3. 数据库策略

### MVP

默认使用 SQLite：

```text
sqlite:///./data/smart_gallery.db
```

优点：

- 零依赖启动。
- 适合个人本地图库。
- 方便备份与迁移。

### 进阶部署

切换到 PostgreSQL：

```text
postgresql+psycopg://smart_gallery:smart_gallery@localhost:5432/smart_gallery
```

推荐在 PostgreSQL 中启用 `pgvector`，用于图片 embedding 的向量检索。

## 4. AI 能力选型

### OCR

首选：

- PaddleOCR：中文效果好，适合截图、票据、文档图片。

备选：

- EasyOCR：上手简单。
- Tesseract：部署轻，但中文效果通常弱于 PaddleOCR。

### 图片描述

本地模型：

- BLIP / BLIP-2：图片 caption。
- LLaVA / Qwen2.5-VL：图片问答和更强理解能力。

云 Provider：

- OpenAI Vision API：作为可选增强，不作为默认依赖。

### 向量检索

MVP 可先保存 embedding 数据结构，检索层分阶段实现。

推荐路径：

1. 个人本地版：SQLite + sqlite-vec。
2. 服务端版：PostgreSQL + pgvector。
3. 大规模版：Qdrant。

### 图片相似度

推荐模型：

- CLIP / OpenCLIP：图文统一向量空间，适合语义搜索。
- sentence-transformers 中的 CLIP 包装模型：上手更快。

## 5. 文件存储

SmartGalleryAI 默认不复制原图，只保存：

- 原图绝对路径或库内相对路径。
- 文件 SHA256。
- 缩略图缓存。
- 识别结果与索引。

推荐目录：

```text
data/
  media/          # 可选，托管上传图片
  thumbnails/     # 缩略图缓存
  smart_gallery.db
```

## 6. 后端模块划分

```text
backend/app/
  api/            # HTTP API 路由
  core/           # 配置、日志、安全策略
  db/             # 数据库连接与基础模型
  models/         # SQLAlchemy 模型
  schemas/        # Pydantic 请求响应模型
  services/       # 导入、缩略图、搜索等业务服务
  services/analyzers/
                  # OCR、Caption、Embedding Provider 接口
  workers/        # Celery 任务入口
```

## 7. API 设计方向

第一阶段 API：

- `GET /api/v1/health`
- `POST /api/v1/assets/scan`
- `GET /api/v1/assets`
- `GET /api/v1/assets/{asset_id}`
- `POST /api/v1/assets/{asset_id}/analyze`
- `GET /api/v1/search`

第二阶段 API：

- 相似图片搜索。
- 自动相册。
- 标签编辑。
- 重复图片检测。
- 图片问答。

## 8. 部署建议

### 本地个人版

- FastAPI + SQLite。
- 可选 Redis。
- AI 模型按需安装。

### 私有服务器版

- FastAPI + PostgreSQL + Redis + Celery。
- Nginx 反向代理。
- 模型 Worker 独立进程。

### NAS / 家庭服务器版

- Docker Compose。
- 图片目录只读挂载。
- 缩略图和数据库单独挂载卷。

## 9. 为什么不是一开始就全本地大模型

全本地模型很吸引人，但开源项目第一阶段应先保证：

- 用户能轻松启动。
- 导入图片不会崩。
- 搜索和数据模型稳定。
- AI Provider 可替换。

因此建议把重模型放进 optional dependencies 和独立 Worker，而不是核心 API 的硬依赖。

## 10. 推荐 MVP 技术组合

最终推荐第一版采用：

```text
FastAPI
SQLAlchemy 2
SQLite
Pillow
Celery + Redis
Pydantic Settings
PaddleOCR optional
CLIP/OpenCLIP optional
pytest + Ruff
```

这套组合足够轻、足够 Python、也足够向完整智能图库演进。

