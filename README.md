# SmartGalleryAI

SmartGalleryAI 是一个本地优先的智能图库开源项目构想与 Python 后端脚手架。它的目标不是再做一个普通相册，而是把图片自动整理成可检索、可分析、可扩展的个人视觉知识库。

## 项目定位

用户导入本地图片目录后，系统自动完成：

- 图片基础元数据提取：尺寸、格式、大小、路径、哈希。
- OCR 文本识别：截图、票据、文档图片可搜索。
- 图片语义理解：生成描述、标签、场景与对象信息。
- 相似图片检索：用向量索引找到近似图片。
- 智能搜索：支持关键词、标签、OCR、语义搜索组合。
- 本地优先：默认不上传原图，云模型作为可选 Provider。

## 当前项目内容

这是第一版开源项目胚子，包含：

- FastAPI 后端入口。
- SQLAlchemy 数据模型。
- 图片目录扫描服务。
- 缩略图生成和访问 API。
- 单图分析与同步批量分析 API。
- 分页图库列表、服务端筛选和基础搜索 API。
- 图片分析 Provider 接口设计。
- 静态前端图库工作台。
- 技术栈书与产品构思文档。

## 快速开始

```powershell
cd SmartGalleryAI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --app-dir backend
```

数据库 schema 由 Alembic 管理。首次启动或代码升级后请先执行 `alembic upgrade head`。

访问：

- 图库工作台：http://127.0.0.1:8000/app
- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/v1/health

当前前端会优先显示缩略图；如果开发环境尚未安装 Pillow，后端会回退到原图预览，服务仍可启动和浏览图片。

默认 OCR Provider 是 `noop`，用于保证基础服务不依赖重型 AI 包。需要启用 PaddleOCR 时再安装：

```powershell
pip install -e ".[ai]"
$env:SMART_GALLERY_OCR_PROVIDER="paddleocr"
```

## 扫描图片目录

启动服务后调用：

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/assets/scan `
  -H "Content-Type: application/json" `
  -d "{\"root_path\":\"D:\\Pictures\"}"
```

## 常用 API

- `GET /api/v1/assets?filter=all&limit=60&offset=0`：分页列出图片，返回 `items` 和 `total`。
- `GET /api/v1/search?q=金额&filter=ocr`：搜索路径、OCR、描述和标签。
- `POST /api/v1/assets/{asset_id}/analyze`：分析单张图片。
- `POST /api/v1/assets/analyze`：同步批量分析，默认处理未分析图片。

批量分析示例：

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/assets/analyze `
  -H "Content-Type: application/json" `
  -d "{\"filter\":\"unanalyzed\",\"limit\":50,\"reanalyze\":false}"
```

## 文档

- [技术栈书](docs/TECH_STACK.md)
- [产品构思](docs/PRODUCT_BLUEPRINT.md)
- [架构说明](docs/ARCHITECTURE.md)
- [路线图](docs/ROADMAP.md)
- [MVP 执行计划](docs/MVP_EXECUTION_PLAN.md)

## 开源方向

SmartGalleryAI 建议优先服务个人用户、摄影师、设计师、知识工作者和经常处理截图/资料图的人群。项目核心价值是“找得到”和“看得懂”，界面漂亮是加分项，但后端索引、识别、搜索与数据可迁移才是长期护城河。
