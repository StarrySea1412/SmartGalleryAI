from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.image_asset import ImageAsset
from app.services.asset_filters import AssetFilter, asset_filter_condition, normalize_asset_filter


@dataclass(frozen=True)
class AssetPage:
    items: list[ImageAsset]
    total: int
    limit: int
    offset: int
    filter: AssetFilter


def list_image_assets(
    *,
    session: Session,
    limit: int = 50,
    offset: int = 0,
    asset_filter: str | None = None,
) -> AssetPage:
    normalized_filter = normalize_asset_filter(asset_filter)
    filter_condition = asset_filter_condition(normalized_filter)

    id_statement = select(ImageAsset.id).outerjoin(ImageAsset.analysis)
    statement = select(ImageAsset).outerjoin(ImageAsset.analysis)

    if filter_condition is not None:
        id_statement = id_statement.where(filter_condition)
        statement = statement.where(filter_condition)

    total = session.scalar(select(func.count()).select_from(id_statement.subquery())) or 0
    items = list(
        session.scalars(
            statement.order_by(ImageAsset.imported_at.desc()).offset(offset).limit(limit)
        )
    )

    return AssetPage(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        filter=normalized_filter,
    )

