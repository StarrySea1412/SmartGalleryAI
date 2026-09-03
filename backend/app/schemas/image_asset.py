from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

AssetFilterValue = Literal["all", "unanalyzed", "failed", "ocr", "recent"]


class ScanRequest(BaseModel):
    root_path: Path = Field(..., description="Directory to scan for images.")


class ScanResponse(BaseModel):
    scanned: int
    imported: int
    skipped: int


class ScanPathSuggestion(BaseModel):
    label: str
    path: str


class ImageAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    caption: str | None = None
    ocr_text: str | None = None
    labels: list[str] | None = None
    dominant_colors: list[str] | None = None
    status: str = "pending"
    provider: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    embedding_model: str | None = None
    analyzed_at: datetime | None = None


class ImageAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    path: str
    sha256: str
    mime_type: str | None
    file_size: int
    width: int | None
    height: int | None
    thumbnail_path: str | None = None
    imported_at: datetime
    last_scanned_at: datetime
    updated_at: datetime
    analysis: ImageAnalysisRead | None = None

    @computed_field
    @property
    def thumbnail_url(self) -> str | None:
        if self.thumbnail_path is None:
            return None
        return f"/api/v1/assets/{self.id}/thumbnail"

    @computed_field
    @property
    def file_url(self) -> str:
        return f"/api/v1/assets/{self.id}/file"


class AssetListResponse(BaseModel):
    items: list[ImageAssetRead]
    total: int
    limit: int
    offset: int
    filter: AssetFilterValue


class BatchAnalyzeRequest(BaseModel):
    asset_ids: list[str] | None = None
    filter: AssetFilterValue = "unanalyzed"
    limit: int = Field(50, ge=1, le=200)
    reanalyze: bool = False


class BatchAnalyzeItemRead(BaseModel):
    asset: ImageAssetRead
    status: str
    skipped: bool = False
    error_message: str | None = None


class BatchAnalyzeResponse(BaseModel):
    requested: int
    analyzed: int
    succeeded: int
    failed: int
    skipped: int
    items: list[BatchAnalyzeItemRead]
