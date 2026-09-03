from dataclasses import dataclass

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models.image_asset import ImageAnalysis, ImageAsset
from app.services.asset_filters import AssetFilter, asset_filter_condition, normalize_asset_filter
from app.services.search_index import search_index_asset_ids


@dataclass(frozen=True)
class SearchResultItem:
    asset: ImageAsset
    matched_fields: list[str]
    snippet: str | None


@dataclass(frozen=True)
class SearchResults:
    items: list[SearchResultItem]
    total: int
    limit: int
    offset: int
    filter: AssetFilter


def search_assets(
    query: str,
    *,
    session: Session,
    limit: int = 50,
    offset: int = 0,
    asset_filter: str | None = None,
) -> SearchResults:
    normalized_filter = normalize_asset_filter(asset_filter)
    normalized_query = query.strip()
    if not normalized_query:
        return SearchResults(
            items=[],
            total=0,
            limit=limit,
            offset=offset,
            filter=normalized_filter,
        )

    fts_asset_ids = search_index_asset_ids(session, normalized_query)
    criteria = search_criteria(normalized_query, fts_asset_ids=fts_asset_ids)
    filter_condition = asset_filter_condition(normalized_filter)
    matching_ids = (
        select(ImageAsset.id)
        .outerjoin(ImageAsset.analysis)
        .where(criteria)
    )
    statement = select(ImageAsset).outerjoin(ImageAsset.analysis).where(criteria)

    if filter_condition is not None:
        matching_ids = matching_ids.where(filter_condition)
        statement = statement.where(filter_condition)

    total = session.scalar(select(func.count()).select_from(matching_ids.subquery())) or 0

    assets = list(
        session.scalars(
            statement.order_by(ImageAsset.imported_at.desc()).offset(offset).limit(limit)
        )
    )

    return SearchResults(
        items=[build_search_result(asset, normalized_query) for asset in assets],
        total=total,
        limit=limit,
        offset=offset,
        filter=normalized_filter,
    )


def search_criteria(query: str, *, fts_asset_ids: list[str] | None = None):
    pattern = f"%{query}%"
    criteria = [
        ImageAsset.path.ilike(pattern),
        ImageAnalysis.ocr_text.ilike(pattern),
        ImageAnalysis.caption.ilike(pattern),
        cast(ImageAnalysis.labels, String).ilike(pattern),
    ]
    if fts_asset_ids:
        criteria.append(ImageAsset.id.in_(fts_asset_ids))

    return or_(*criteria)


def build_search_result(asset: ImageAsset, query: str) -> SearchResultItem:
    matched_fields: list[str] = []
    snippet: str | None = None

    if contains_query(asset.path, query):
        matched_fields.append("path")
        snippet = snippet or make_snippet(asset.path, query)

    analysis = asset.analysis
    if analysis is not None:
        if contains_query(analysis.ocr_text, query):
            matched_fields.append("ocr_text")
            snippet = snippet or make_snippet(analysis.ocr_text, query)
        if contains_query(analysis.caption, query):
            matched_fields.append("caption")
            snippet = snippet or make_snippet(analysis.caption, query)
        labels_text = " ".join(analysis.labels or [])
        if contains_query(labels_text, query):
            matched_fields.append("labels")
            snippet = snippet or make_snippet(labels_text, query)

    return SearchResultItem(asset=asset, matched_fields=matched_fields, snippet=snippet)


def contains_query(value: str | None, query: str) -> bool:
    if not value:
        return False
    return query.lower() in value.lower()


def make_snippet(value: str | None, query: str, *, radius: int = 48) -> str | None:
    if not value:
        return None

    normalized_value = value.lower()
    normalized_query = query.lower()
    index = normalized_value.find(normalized_query)
    if index < 0:
        return value[: radius * 2]

    start = max(0, index - radius)
    end = min(len(value), index + len(query) + radius)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(value) else ""
    return f"{prefix}{value[start:end]}{suffix}"
