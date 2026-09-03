from pydantic import BaseModel

from app.schemas.image_asset import ImageAssetRead


class SearchResultItemRead(BaseModel):
    asset: ImageAssetRead
    matched_fields: list[str]
    snippet: str | None = None


class SearchResponse(BaseModel):
    items: list[SearchResultItemRead]
    total: int
    limit: int
    offset: int
