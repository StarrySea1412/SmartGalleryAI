# 架构说明

## 分层

```text
Client
  |
FastAPI HTTP API
  |
Application Services
  |
SQLAlchemy Models / File Storage / AI Providers
  |
SQLite or PostgreSQL / Redis / Vector Index
```

## 数据流

1. 用户提交图片目录。
2. 后端扫描文件，过滤支持的图片格式。
3. 计算 SHA256，读取尺寸和格式。
4. 写入 `image_assets` 表。
5. 后台任务生成缩略图、OCR、描述、embedding。
6. 搜索接口聚合关键词、标签、OCR 和向量结果。

## 核心实体

### ImageAsset

表示一张被索引的图片，保存文件路径、哈希、尺寸、大小和导入时间。

### ImageAnalysis

表示 AI 分析结果，保存描述、OCR 文本、标签、颜色、embedding 模型信息。

## Provider 设计

AI 能力通过接口隔离：

- `OCRProvider`
- `CaptionProvider`
- `EmbeddingProvider`

这样可以支持：

- 本地 PaddleOCR。
- 本地 CLIP。
- 云 Vision API。
- 用户自定义模型服务。

## 任务队列

耗时任务不应阻塞 API：

- 批量扫描。
- 缩略图生成。
- OCR。
- 图片描述。
- embedding。
- 重建索引。

第一阶段可以同步调用，第二阶段迁移到 Celery Worker。

