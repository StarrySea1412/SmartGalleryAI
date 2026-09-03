import mimetypes
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models.image_asset import ImageAsset
from app.schemas.image_asset import (
    AssetFilterValue,
    AssetListResponse,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    ImageAssetRead,
    ScanPathSuggestion,
    ScanRequest,
    ScanResponse,
)
from app.services.analysis import analyze_image_asset, analyze_image_assets
from app.services.asset_library import list_image_assets
from app.services.importer import scan_image_directory
from app.services.scan_paths import get_scan_path_suggestions

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]
LimitParam = Annotated[int, Query(ge=1, le=200)]
OffsetParam = Annotated[int, Query(ge=0)]
AssetFilterParam = Annotated[AssetFilterValue, Query()]


@router.post("/scan", response_model=ScanResponse)
def scan_assets(
    payload: ScanRequest,
    session: SessionDep,
) -> ScanResponse:
    try:
        result = scan_image_directory(payload.root_path, session=session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ScanResponse(**result)


@router.get("/scan/suggestions", response_model=list[ScanPathSuggestion])
def scan_path_suggestions() -> list[dict[str, str]]:
    return get_scan_path_suggestions()


@router.get("", response_model=AssetListResponse)
def list_assets(
    session: SessionDep,
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
    filter: AssetFilterParam = "all",
) -> AssetListResponse:
    page = list_image_assets(
        session=session,
        limit=limit,
        offset=offset,
        asset_filter=filter,
    )
    return AssetListResponse(
        items=page.items,
        total=page.total,
        limit=page.limit,
        offset=page.offset,
        filter=page.filter,
    )


@router.post("/analyze", response_model=BatchAnalyzeResponse)
def analyze_assets(
    payload: BatchAnalyzeRequest,
    session: SessionDep,
) -> BatchAnalyzeResponse:
    result = analyze_image_assets(
        session=session,
        asset_ids=payload.asset_ids,
        asset_filter=payload.filter,
        limit=payload.limit,
        reanalyze=payload.reanalyze,
    )
    return BatchAnalyzeResponse(
        requested=result.requested,
        analyzed=result.analyzed,
        succeeded=result.succeeded,
        failed=result.failed,
        skipped=result.skipped,
        items=[
            {
                "asset": item.asset,
                "status": item.status,
                "skipped": item.skipped,
                "error_message": item.error_message,
            }
            for item in result.items
        ],
    )


@router.get("/{asset_id}/thumbnail")
def get_asset_thumbnail(asset_id: str, session: SessionDep) -> FileResponse:
    asset = session.get(ImageAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Image asset not found")
    if asset.thumbnail_path is None:
        raise HTTPException(status_code=404, detail="Thumbnail not generated")

    thumbnail_path = Path(asset.thumbnail_path)
    if not thumbnail_path.is_file():
        raise HTTPException(status_code=404, detail="Thumbnail file not found")

    return FileResponse(thumbnail_path, media_type="image/webp")


@router.get("/{asset_id}/file")
def get_asset_file(asset_id: str, session: SessionDep) -> FileResponse:
    asset = session.get(ImageAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Image asset not found")

    image_path = Path(asset.path)
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image file not found")

    media_type = asset.mime_type or mimetypes.guess_type(image_path.name)[0]
    return FileResponse(image_path, media_type=media_type or "application/octet-stream")


@router.post("/{asset_id}/analyze", response_model=ImageAssetRead)
def analyze_asset(asset_id: str, session: SessionDep) -> ImageAsset:
    asset = session.get(ImageAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Image asset not found")

    analyze_image_asset(asset, session=session)
    return asset


@router.get("/{asset_id}", response_model=ImageAssetRead)
def get_asset(asset_id: str, session: SessionDep) -> ImageAsset:
    asset = session.get(ImageAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Image asset not found")
    return asset
