# 路线图

SmartGalleryAI 的路线按“先可靠导入，再可搜索，再智能理解，再产品化”的顺序推进。
当前代码已经完成 Phase 0 的后端胚子，下一阶段重点是把图片识别链路跑通，形成真正可用的 MVP。

## 当前状态

已完成：

- FastAPI 后端结构。
- SQLAlchemy 数据模型：`ImageAsset`、`ImageAnalysis`。
- Alembic 迁移入口和首个 schema 迁移。
- 图片目录扫描 API：计算 SHA256、读取尺寸、格式、大小并入库。
- 缩略图生成和访问 API。
- 单图分析 API 和分析状态流转。
- 同步批量分析 API，支持按筛选范围或指定图片执行。
- 可配置 OCR Provider：`noop` 和可选 `paddleocr`。
- 基础关键词搜索 API，返回命中字段和 snippet，并保留 SQLite FTS5 可选索引与 `LIKE` fallback。
- 图片资产分页列表、服务端筛选和详情 API。
- 前端图库工作台：扫描、筛选、搜索、缩略图/原图预览网格、详情面板、单图/批量分析。
- OCR / Caption / Embedding Provider 抽象接口。
- SQLite 默认数据库配置。
- Redis、PostgreSQL、pgvector 的 Docker Compose 基础服务。

待补齐：

- 后台任务化的扫描和分析队列。
- 大图库性能优化，例如虚拟滚动、FTS5 深化和增量索引重建。

## Phase 1: 可用 MVP

目标：导入一个本地图片目录后，用户可以浏览图片、查看缩略图、执行 OCR，并用关键词找到图片。

### 1. 数据和迁移稳定化

- 接入 Alembic，停止依赖 `Base.metadata.create_all` 作为长期方案。
- 为 `image_assets.path`、`image_assets.sha256`、`image_assets.imported_at` 保留索引。
- 为 `ImageAnalysis` 增加分析状态字段：`pending`、`running`、`succeeded`、`failed`。
- 增加错误信息字段，方便定位某张图为什么没有识别成功。
- 约定版本升级时的数据迁移流程。
- 运行时不再依赖 `Base.metadata.create_all` 创建业务表，启动前通过 Alembic 迁移建库。

验收标准：

- 新环境可以通过迁移创建数据库。
- 已有数据库可以无损升级。
- 单张图片分析失败不会影响整个扫描任务。

### 2. 缩略图生成

- 使用 Pillow 生成固定宽度缩略图，优先保留原图比例。
- 缩略图文件名使用图片 SHA256，避免路径变化导致缓存失效。
- 增加缩略图字段或可计算路径。
- 增加缩略图访问 API，例如 `GET /api/v1/assets/{asset_id}/thumbnail`。
- 扫描导入后可以同步生成缩略图，后续再迁移到后台任务。

验收标准：

- 导入 1000 张图片后，缩略图目录结构稳定。
- 无法打开的图片会被跳过并记录错误。
- 列表 API 能返回缩略图可访问地址。

### 3. OCR 识别链路

- 保留 `NoopOCRProvider` 作为默认空实现。
- 新增 PaddleOCR Provider，放入 optional dependency，避免基础安装过重。
- 增加 `POST /api/v1/assets/{asset_id}/analyze`，对单张图片执行识别。
- 将 OCR 文本写入 `ImageAnalysis.ocr_text`。
- 记录 Provider 名称、耗时和分析时间。

验收标准：

- 中文截图可以被识别并保存文本。
- 未安装 PaddleOCR 时服务仍可启动。
- 分析接口对不存在的图片、损坏图片、Provider 异常都有明确响应。

### 4. 基础搜索

- 增加 `GET /api/v1/search?q=...`。
- 第一版先搜索路径、OCR 文本、caption、labels。
- SQLite 阶段保留 `LIKE` 兼容搜索，并维护可选 FTS5 索引用于后续优化。
- 搜索结果返回命中来源：`path`、`ocr_text`、`caption`、`labels`。

验收标准：

- 能通过中文 OCR 文本找到截图。
- 能解释每条结果为什么命中。
- 搜索接口支持分页。

### 5. 最小图库前端

- 第一屏直接是图库工作台，不做营销页。
- 支持图片网格、搜索框、详情侧栏。
- 支持服务端筛选、分页总数、当前页批量分析和未分析图片批量分析。
- 详情侧栏展示路径、尺寸、大小、OCR 文本、标签、描述。
- 对未分析、分析中、失败的图片有清晰状态。

验收标准：

- 用户可以从浏览器完成“看图、搜索、打开详情”的闭环。
- 5000 张图片列表分页或虚拟滚动不卡顿。

## Phase 2: 智能搜索

目标：从“能搜文字”升级到“能搜画面内容”和“找相似图片”。

### 1. Caption 和标签

- 增加 Caption Provider，实现图片描述生成。
- 自动生成少量高质量标签，不追求一开始覆盖所有类别。
- 标签支持人工编辑。

### 2. Embedding 和向量检索

- 接入 CLIP / OpenCLIP Provider。
- 为每张图片生成 embedding。
- 本地个人版优先评估 SQLite + sqlite-vec。
- PostgreSQL 部署版使用 pgvector。
- 增加相似图片 API，例如 `GET /api/v1/assets/{asset_id}/similar`。

### 3. 自然语言搜索

- 将查询文本转为 embedding。
- 混合排序：关键词命中 + OCR 命中 + 向量相似度。
- 搜索结果解释保留为产品核心能力。

验收标准：

- 可以搜索“蓝色按钮界面”“海边夜景”“有金额和日期的票据”。
- 可以从一张图找到视觉相似图片。
- 重建索引过程可中断、可恢复。

## Phase 3: 整理能力

目标：从搜索工具变成图片资料库。

- 自动相册：按时间、地点、场景、文档类型聚类。
- 重复图片清理：基于 SHA256、感知哈希、embedding 相似度分层判断。
- 批量操作：打标签、隐藏、重新分析、导出。
- 数据导出：JSON / CSV / SQLite 备份。
- 导入策略：只读挂载目录、托管上传目录、增量扫描。

## Phase 4: 产品化和生态

目标：让项目适合长期自托管和开源协作。

- NAS / 家庭服务器部署指南。
- Docker 镜像和 Compose 一键启动。
- 后台 Worker 独立扩缩容。
- Provider 插件规范。
- 权限和多用户模式。
- 公开的贡献指南和测试矩阵。

## 优先级原则

1. 先保证导入和索引稳定，再堆 AI 能力。
2. AI Provider 必须可选，基础服务不能因为模型没装而不可用。
3. 搜索结果要能解释命中原因，这是产品差异化。
4. 本地优先是默认路线，云模型只能作为增强选项。
5. 每个阶段都要能处理至少 5000 张图片，避免只在 demo 数据上可用。
