# MVP 执行计划

本文档用于指导 SmartGalleryAI 接下来一轮开发。目标不是一次性做完整智能图库，而是把“导入图片、识别图片、搜索图片、查看结果”这条主链路做稳。

## MVP 目标

用户选择一个本地图片目录后，系统应该能够：

1. 扫描并登记图片资产。
2. 为图片生成缩略图。
3. 对图片执行 OCR 识别。
4. 保存识别结果和分析状态。
5. 通过关键词搜索路径、OCR 文本、标签和描述。
6. 在图片详情中看到元数据、缩略图、OCR 文本和分析状态。

## 当前基础

已有能力：

- `POST /api/v1/assets/scan`：扫描目录并导入图片。
- `GET /api/v1/assets`：分页列出图片资产。
- `GET /api/v1/assets/{asset_id}`：查看图片资产详情。
- `ImageAsset`：保存路径、SHA256、尺寸、大小、MIME 类型。
- `ImageAnalysis`：保存 caption、OCR 文本、标签、颜色、embedding。
- `OCRProvider`、`CaptionProvider`、`EmbeddingProvider`：AI Provider 接口。
- Alembic 迁移入口和第一版 schema 迁移。

当前收口后剩余缺口：

- 扫描和分析仍是同步流程，大图目录下需要迁移到后台任务。
- 大图库体验还需要虚拟滚动、增量索引重建和更完整的性能测试。

## 建议开发顺序

### Milestone 1: 数据模型和迁移

状态：已完成 Phase 1 收口实现，后续需要在完整依赖环境中跑测试和迁移 smoke test。

目标：让后续功能有稳定落点。

任务：

- 已初始化 Alembic。
- 已将当前模型生成第一版迁移。
- 已为 `ImageAnalysis` 增加：
  - `status`
  - `error_message`
  - `provider`
  - `duration_ms`
- 已为 `ImageAsset` 增加：
  - `thumbnail_path`
  - `last_scanned_at`
- 已补充模型和 schema 测试。
- 已将运行时建表职责收敛到 Alembic，应用启动不再调用 `Base.metadata.create_all` 创建业务表。
- 已补充 `image_assets.imported_at` 索引。

接口影响：

- `ImageAssetRead` 返回 `thumbnail_url` 或 `thumbnail_path`。
- `ImageAnalysisRead` 返回状态、错误、Provider 信息。

验收：

- `pytest` 通过。
- 空数据库可以迁移到最新版。
- 旧字段不丢失。

### Milestone 2: 缩略图服务

状态：已完成第一轮实现，后续可在安装依赖后补跑完整 pytest。

目标：图片列表能快速展示。

任务：

- 已新增 `services/thumbnails.py`。
- 已使用 Pillow 生成最长边 512px 的缩略图。
- 已将缩略图保存到 `data/thumbnails/{sha256[:2]}/{sha256}.webp`。
- 已在导入图片时生成或复用缩略图。
- 已增加 `GET /api/v1/assets/{asset_id}/thumbnail`。
- 损坏图片会跳过缩略图生成，不中断扫描。

验收：

- 导入 JPG、PNG、WEBP 后都能生成缩略图。
- 重复扫描不会重复生成同一个缩略图。
- 列表页无需读取原图即可展示。

### Milestone 3: 单图分析 API

状态：已完成第一轮实现，当前默认使用 `NoopOCRProvider` 跑通状态流转。

目标：先把识别链路对单张图片跑通。

任务：

- 已新增 `services/analysis.py`。
- 已增加 `POST /api/v1/assets/{asset_id}/analyze`。
- 已默认使用 `NoopOCRProvider`，保证无 AI 依赖也能开发。
- 已在分析开始时写入 `running` 状态。
- 已在成功后写入 `succeeded`、`ocr_text`、`provider`、`duration_ms`、`analyzed_at`。
- 已在异常后写入 `failed`、`error_message`、`duration_ms`、`analyzed_at`。

验收：

- 同一张图片可以重复分析并覆盖旧结果。
- Provider 异常不会让 API 进程崩溃。
- 分析状态能在详情 API 中看到。

### Milestone 4: PaddleOCR Provider

状态：已完成第一轮接入口，实现了配置项、Provider 工厂和 PaddleOCR 懒加载封装。

目标：真正识别中文截图和文档图片。

任务：

- 已新增 `services/analyzers/paddle_ocr.py`。
- 已保持 PaddleOCR 仅在安装 `.[ai]` 并配置启用后使用。
- 已增加配置项：`ocr_provider=noop|paddleocr`。
- 已对 PaddleOCR 初始化做懒加载，避免服务启动过慢。
- 已将多行结果合并成可搜索文本。

验收：

- 中文截图识别结果可以写入 `ImageAnalysis.ocr_text`。
- 未安装 PaddleOCR 时选择该 Provider 会返回明确错误。
- 基础安装不需要下载模型。

### Milestone 5: 基础搜索

状态：已完成 Phase 1 收口实现，当前保留 SQL `LIKE` fallback，并维护 SQLite FTS5 可选索引。

目标：让“识别图片”变成“找得到图片”。

任务：

- 已新增 `GET /api/v1/search?q=&limit=&offset=`。
- 已搜索字段：
  - `ImageAsset.path`
  - `ImageAnalysis.ocr_text`
  - `ImageAnalysis.caption`
  - `ImageAnalysis.labels`
- 已返回命中原因和图片摘要。
- 搜索会尝试使用 SQLite FTS5 命中的 asset id，并继续使用 SQL `LIKE` 保证中文 substring 搜索兼容。
- 搜索支持与图库列表一致的 `filter` 参数。

响应建议：

```json
{
  "items": [
    {
      "asset": {},
      "matched_fields": ["ocr_text"],
      "snippet": "错误码 500 ..."
    }
  ],
  "limit": 50,
  "offset": 0,
  "total": 1
}
```

验收：

- 输入截图中的中文文本可以找到图片。
- 搜索结果支持分页。
- 每个结果能显示命中字段。

### Milestone 6: 最小前端工作台

状态：已完成 Phase 1 收口工作台实现，由 FastAPI 挂载到 `/app`。

目标：给项目一个能用的第一屏。

任务：

- 已建立 `web/` 前端应用目录。
- 已用图库网格展示缩略图。
- 已在缩略图缺失时回退到原图预览。
- 已实现顶部搜索框并调用 `/api/v1/search`。
- 已实现右侧详情面板。
- 已在详情中显示 OCR 文本、路径、尺寸、大小、分析状态。
- 已提供“分析此图”按钮。
- 已将筛选改为服务端筛选。
- 已增加分页总数、当前页批量分析和未分析图片批量分析。

验收：

- 用户不需要 Swagger 就能完成浏览和搜索。
- 图片状态清晰：未分析、分析中、成功、失败。
- 5000 张图片通过分页或虚拟滚动保持可用。

## API 清单

MVP 应保留或新增：

- `GET /api/v1/health`
- `POST /api/v1/assets/scan`
- `GET /api/v1/assets`
- `GET /api/v1/assets/{asset_id}`
- `GET /api/v1/assets/{asset_id}/thumbnail`
- `POST /api/v1/assets/{asset_id}/analyze`
- `POST /api/v1/assets/analyze`
- `GET /api/v1/search`

`GET /api/v1/assets` 返回分页对象：`items`、`total`、`limit`、`offset`、`filter`。
`GET /api/v1/search` 支持 `filter=all|unanalyzed|failed|ocr|recent`。

## 数据状态设计

建议 `ImageAnalysis.status` 使用以下枚举值：

- `pending`：已创建记录，但尚未开始。
- `running`：正在分析。
- `succeeded`：分析成功。
- `failed`：分析失败，可查看 `error_message`。

后续批量任务可增加独立 `AnalysisJob` 表，但 MVP 可以先不引入，避免过早复杂化。

## 测试重点

- 扫描不存在目录返回 400。
- 重复扫描同一批图片不会重复入库。
- 损坏图片不会中断整个扫描。
- 缩略图路径稳定。
- 单图分析成功和失败都会落库。
- 搜索能命中 OCR 文本。
- 未安装 AI 依赖时后端仍可启动。

## 风险和取舍

- PaddleOCR 依赖较重，应保持 optional，不能进入基础启动路径。
- SQLite `LIKE` 对大量数据性能一般，但足够支撑第一版验证；后续升级 FTS5。
- embedding 不应抢在 OCR 和缩略图之前做，否则项目会变重但用户闭环还没形成。
- 先做单图分析，再做批量后台任务，能降低调试难度。

## 下一步最小任务

建议下一次编码可以从以下方向继续：

1. 安装项目依赖并跑完整 `pytest` 和迁移 smoke test。
2. 启动后端，人工验证 `/app` 的扫描、筛选、搜索、批量分析流程。
3. 将扫描和批量分析迁移到后台任务，增加进度查询。
4. 增加大图库虚拟滚动和真实 5000+ 图片性能测试。
5. 深化 FTS5 重建和损坏索引恢复入口。

当前 MVP 闭环已经具备可验收雏形：扫描目录、生成缩略图或原图预览、服务端筛选、单图/批量分析、关键词搜索、前端查看详情。
