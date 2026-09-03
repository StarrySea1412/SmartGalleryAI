from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.image_asset import AnalysisStatus, ImageAnalysis, ImageAsset, utcnow
from app.services.analyzers.base import OCRProvider
from app.services.analyzers.factory import get_ocr_provider
from app.services.asset_filters import asset_filter_condition, normalize_asset_filter
from app.services.search_index import sync_asset_search_index


@dataclass(frozen=True)
class BatchAnalysisItem:
    asset: ImageAsset
    status: str
    skipped: bool
    error_message: str | None = None


@dataclass(frozen=True)
class BatchAnalysisResult:
    requested: int
    analyzed: int
    succeeded: int
    failed: int
    skipped: int
    items: list[BatchAnalysisItem]


def analyze_image_asset(
    asset: ImageAsset,
    *,
    session: Session,
    ocr_provider: OCRProvider | None = None,
) -> ImageAnalysis:
    analysis = get_or_create_analysis(asset, session=session)
    analysis.status = AnalysisStatus.RUNNING.value
    analysis.provider = None
    analysis.error_message = None
    analysis.duration_ms = None
    session.flush()

    started_at = perf_counter()
    try:
        provider = ocr_provider or get_ocr_provider()
        analysis.provider = provider.__class__.__name__
        image_path = Path(asset.path)
        if not image_path.is_file():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        ocr_result = provider.extract_text(image_path)
        analysis.ocr_text = ocr_result.text
        analysis.status = AnalysisStatus.SUCCEEDED.value
    except Exception as exc:
        analysis.status = AnalysisStatus.FAILED.value
        analysis.error_message = str(exc)
    finally:
        analysis.duration_ms = int((perf_counter() - started_at) * 1000)
        analysis.analyzed_at = utcnow()
        session.commit()
        sync_asset_search_index(session, asset)
        session.refresh(analysis)

    return analysis


def get_or_create_analysis(asset: ImageAsset, *, session: Session) -> ImageAnalysis:
    if asset.analysis is not None:
        return asset.analysis

    analysis = ImageAnalysis(asset=asset)
    session.add(analysis)
    return analysis


def analyze_image_assets(
    *,
    session: Session,
    asset_ids: list[str] | None = None,
    asset_filter: str | None = None,
    limit: int = 50,
    reanalyze: bool = False,
) -> BatchAnalysisResult:
    assets = select_batch_assets(
        session=session,
        asset_ids=asset_ids,
        asset_filter=asset_filter,
        limit=limit,
    )
    items: list[BatchAnalysisItem] = []
    analyzed = 0
    succeeded = 0
    failed = 0
    skipped = 0

    for asset in assets:
        if should_skip_analysis(asset, reanalyze=reanalyze):
            skipped += 1
            status = (
                asset.analysis.status
                if asset.analysis is not None
                else AnalysisStatus.PENDING.value
            )
            items.append(
                BatchAnalysisItem(
                    asset=asset,
                    status=status,
                    skipped=True,
                    error_message=(
                        asset.analysis.error_message if asset.analysis is not None else None
                    ),
                )
            )
            continue

        analysis = analyze_image_asset(asset, session=session)
        analyzed += 1
        if analysis.status == AnalysisStatus.SUCCEEDED.value:
            succeeded += 1
        elif analysis.status == AnalysisStatus.FAILED.value:
            failed += 1
        items.append(
            BatchAnalysisItem(
                asset=asset,
                status=analysis.status,
                skipped=False,
                error_message=analysis.error_message,
            )
        )

    return BatchAnalysisResult(
        requested=len(assets),
        analyzed=analyzed,
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        items=items,
    )


def select_batch_assets(
    *,
    session: Session,
    asset_ids: list[str] | None,
    asset_filter: str | None,
    limit: int,
) -> list[ImageAsset]:
    statement = select(ImageAsset).outerjoin(ImageAsset.analysis)

    if asset_ids is not None:
        if not asset_ids:
            return []
        statement = statement.where(ImageAsset.id.in_(asset_ids))
    else:
        normalized_filter = normalize_asset_filter(asset_filter, default="unanalyzed")
        filter_condition = asset_filter_condition(normalized_filter)
        if filter_condition is not None:
            statement = statement.where(filter_condition)

    return list(session.scalars(statement.order_by(ImageAsset.imported_at.desc()).limit(limit)))


def should_skip_analysis(asset: ImageAsset, *, reanalyze: bool) -> bool:
    if reanalyze or asset.analysis is None:
        return False
    return asset.analysis.status in {
        AnalysisStatus.RUNNING.value,
        AnalysisStatus.SUCCEEDED.value,
    }
