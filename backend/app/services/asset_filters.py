from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from sqlalchemy import and_, or_
from sqlalchemy.sql.elements import ColumnElement

from app.models.image_asset import AnalysisStatus, ImageAnalysis, ImageAsset

AssetFilter = Literal["all", "unanalyzed", "failed", "ocr", "recent"]
ASSET_FILTERS: set[str] = {"all", "unanalyzed", "failed", "ocr", "recent"}
DEFAULT_ASSET_FILTER: AssetFilter = "all"


def normalize_asset_filter(
    value: str | None,
    *,
    default: AssetFilter = DEFAULT_ASSET_FILTER,
) -> AssetFilter:
    normalized = (value or default).strip().lower()
    if normalized not in ASSET_FILTERS:
        raise ValueError(f"Unsupported asset filter: {value}")
    return cast(AssetFilter, normalized)


def asset_filter_condition(asset_filter: AssetFilter) -> ColumnElement[bool] | None:
    if asset_filter == "all":
        return None
    if asset_filter == "unanalyzed":
        return or_(
            ImageAnalysis.id.is_(None),
            ImageAnalysis.status == AnalysisStatus.PENDING.value,
        )
    if asset_filter == "failed":
        return ImageAnalysis.status == AnalysisStatus.FAILED.value
    if asset_filter == "ocr":
        return and_(
            ImageAnalysis.ocr_text.is_not(None),
            ImageAnalysis.ocr_text != "",
        )
    if asset_filter == "recent":
        return ImageAsset.imported_at >= datetime.now(UTC) - timedelta(days=7)

    raise ValueError(f"Unsupported asset filter: {asset_filter}")
