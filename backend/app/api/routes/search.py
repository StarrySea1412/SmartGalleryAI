from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.image_asset import AssetFilterValue
from app.schemas.search import SearchResponse
from app.services.search import search_assets

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]
SearchQuery = Annotated[str, Query(min_length=1)]
LimitParam = Annotated[int, Query(ge=1, le=200)]
OffsetParam = Annotated[int, Query(ge=0)]
AssetFilterParam = Annotated[AssetFilterValue, Query()]


@router.get("/search", response_model=SearchResponse)
def search(
    q: SearchQuery,
    session: SessionDep,
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
    filter: AssetFilterParam = "all",
) -> SearchResponse:
    results = search_assets(
        q,
        session=session,
        limit=limit,
        offset=offset,
        asset_filter=filter,
    )
    return SearchResponse(
        items=[
            {
                "asset": item.asset,
                "matched_fields": item.matched_fields,
                "snippet": item.snippet,
            }
            for item in results.items
        ],
        total=results.total,
        limit=results.limit,
        offset=results.offset,
    )
