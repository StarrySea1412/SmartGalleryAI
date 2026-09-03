from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from app.core.config import Settings
from app.db.base import Base
from app.models.image_asset import AnalysisStatus, ImageAnalysis, ImageAsset
from app.schemas.image_asset import ImageAssetRead
from app.services.analysis import analyze_image_asset, analyze_image_assets
from app.services.analyzers.base import OCRProvider, OCRResult
from app.services.analyzers.factory import get_ocr_provider
from app.services.analyzers.noop import NoopOCRProvider
from app.services.analyzers.paddle_ocr import parse_paddle_ocr_result
from app.services.asset_library import list_image_assets
from app.services.importer import scan_image_directory
from app.services.search import search_assets
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


def test_scan_image_directory_populates_asset_defaults(tmp_path) -> None:
    image_root = tmp_path / "images"
    thumbnail_root = tmp_path / "thumbnails"
    image_root.mkdir()
    image_path = image_root / "sample.png"
    Image.new("RGB", (24, 16), "red").save(image_path)

    with in_memory_session() as session:
        result = scan_image_directory(image_root, session=session, thumbnail_root=thumbnail_root)
        asset = session.scalar(select(ImageAsset))

        assert result == {"scanned": 1, "imported": 1, "skipped": 0}
        assert asset is not None
        assert asset.path == str(image_path.resolve())
        assert asset.width == 24
        assert asset.height == 16
        assert asset.thumbnail_path is not None
        assert Path(asset.thumbnail_path).is_file()
        assert Path(asset.thumbnail_path).suffix == ".webp"
        assert asset.last_scanned_at is not None

        asset_read = ImageAssetRead.model_validate(asset)
        assert asset_read.thumbnail_path == asset.thumbnail_path
        assert asset_read.thumbnail_url == f"/api/v1/assets/{asset.id}/thumbnail"
        assert asset_read.last_scanned_at == asset.last_scanned_at


def test_scan_image_directory_updates_last_scanned_at_for_existing_assets(tmp_path) -> None:
    image_root = tmp_path / "images"
    thumbnail_root = tmp_path / "thumbnails"
    image_root.mkdir()
    image_path = image_root / "sample.png"
    Image.new("RGB", (24, 16), "blue").save(image_path)

    with in_memory_session() as session:
        first_result = scan_image_directory(
            image_root,
            session=session,
            thumbnail_root=thumbnail_root,
        )
        asset = session.scalar(select(ImageAsset))
        assert asset is not None
        first_last_scanned_at = asset.last_scanned_at
        first_thumbnail_path = asset.thumbnail_path

        second_result = scan_image_directory(
            image_root,
            session=session,
            thumbnail_root=thumbnail_root,
        )
        session.refresh(asset)

        assert first_result == {"scanned": 1, "imported": 1, "skipped": 0}
        assert second_result == {"scanned": 1, "imported": 0, "skipped": 1}
        assert asset.thumbnail_path == first_thumbnail_path
        assert asset.last_scanned_at >= first_last_scanned_at


def test_image_analysis_defaults_to_pending_status() -> None:
    with in_memory_session() as session:
        asset = ImageAsset(
            path="D:/Pictures/sample.png",
            sha256="a" * 64,
            file_size=100,
        )
        session.add(asset)
        session.flush()

        analysis = ImageAnalysis(asset_id=asset.id)
        session.add(analysis)
        session.commit()
        session.refresh(analysis)

        assert analysis.status == AnalysisStatus.PENDING.value
        assert analysis.provider is None
        assert analysis.error_message is None
        assert analysis.duration_ms is None


def test_analyze_image_asset_records_ocr_success(tmp_path) -> None:
    with in_memory_session() as session:
        asset = scan_sample_asset(tmp_path, session=session)

        analysis = analyze_image_asset(
            asset,
            session=session,
            ocr_provider=StaticOCRProvider("hello from image"),
        )

        assert analysis.status == AnalysisStatus.SUCCEEDED.value
        assert analysis.ocr_text == "hello from image"
        assert analysis.provider == "StaticOCRProvider"
        assert analysis.error_message is None
        assert analysis.duration_ms is not None
        assert analysis.analyzed_at is not None


def test_analyze_image_asset_records_provider_failure(tmp_path) -> None:
    with in_memory_session() as session:
        asset = scan_sample_asset(tmp_path, session=session)

        analysis = analyze_image_asset(
            asset,
            session=session,
            ocr_provider=FailingOCRProvider(),
        )

        assert analysis.status == AnalysisStatus.FAILED.value
        assert analysis.provider == "FailingOCRProvider"
        assert analysis.error_message == "OCR failed"
        assert analysis.duration_ms is not None
        assert analysis.analyzed_at is not None


def test_get_ocr_provider_returns_noop_provider() -> None:
    provider = get_ocr_provider(Settings(ocr_provider="noop"))

    assert isinstance(provider, NoopOCRProvider)


def test_get_ocr_provider_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported OCR provider"):
        get_ocr_provider(Settings(ocr_provider="unknown"))


def test_parse_paddle_ocr_result_extracts_text_and_confidence() -> None:
    raw_result = [
        [
            [[[0, 0], [1, 0], [1, 1], [0, 1]], ("第一行", 0.9)],
            [[[0, 2], [1, 2], [1, 3], [0, 3]], ("第二行", 0.8)],
        ]
    ]

    lines, confidences = parse_paddle_ocr_result(raw_result)

    assert lines == ["第一行", "第二行"]
    assert confidences == [0.9, 0.8]


def test_search_assets_matches_path(tmp_path) -> None:
    with in_memory_session() as session:
        asset = scan_sample_asset(tmp_path, session=session)

        results = search_assets("sample", session=session)

        assert results.total == 1
        assert results.items[0].asset.id == asset.id
        assert results.items[0].matched_fields == ["path"]
        assert "sample" in (results.items[0].snippet or "")


def test_search_assets_matches_ocr_text(tmp_path) -> None:
    with in_memory_session() as session:
        asset = scan_sample_asset(tmp_path, session=session)
        session.add(ImageAnalysis(asset=asset, ocr_text="这是一张发票，金额 100 元"))
        session.commit()

        results = search_assets("金额", session=session)

        assert results.total == 1
        assert results.items[0].asset.id == asset.id
        assert results.items[0].matched_fields == ["ocr_text"]
        assert "金额" in (results.items[0].snippet or "")


def test_list_image_assets_filters_on_server() -> None:
    with in_memory_session() as session:
        pending = add_asset(session, "pending.png", "1")
        failed = add_asset(session, "failed.png", "2")
        with_ocr = add_asset(session, "ocr.png", "3")
        session.add(ImageAnalysis(asset=failed, status=AnalysisStatus.FAILED.value))
        session.add(
            ImageAnalysis(
                asset=with_ocr,
                status=AnalysisStatus.SUCCEEDED.value,
                ocr_text="合同编号 ABC",
            )
        )
        session.commit()

        unanalyzed_page = list_image_assets(session=session, asset_filter="unanalyzed")
        failed_page = list_image_assets(session=session, asset_filter="failed")
        ocr_page = list_image_assets(session=session, asset_filter="ocr")

        assert unanalyzed_page.total == 1
        assert unanalyzed_page.items[0].id == pending.id
        assert failed_page.total == 1
        assert failed_page.items[0].id == failed.id
        assert ocr_page.total == 1
        assert ocr_page.items[0].id == with_ocr.id


def test_batch_analyze_assets_runs_unanalyzed_and_skips_succeeded(tmp_path) -> None:
    with in_memory_session() as session:
        fresh = scan_sample_asset(tmp_path, session=session)
        succeeded = add_asset(session, "done.png", "4")
        session.add(
            ImageAnalysis(
                asset=succeeded,
                status=AnalysisStatus.SUCCEEDED.value,
                ocr_text="done",
            )
        )
        session.commit()

        result = analyze_image_assets(
            session=session,
            asset_ids=[fresh.id, succeeded.id],
            limit=10,
            reanalyze=False,
        )

        assert result.requested == 2
        assert result.analyzed == 1
        assert result.succeeded == 1
        assert result.skipped == 1
        assert {item.asset.id for item in result.items} == {fresh.id, succeeded.id}


def test_search_assets_filter_falls_back_without_fts_index() -> None:
    with in_memory_session() as session:
        failed = add_asset(session, "failed-receipt.png", "5")
        succeeded = add_asset(session, "succeeded-receipt.png", "6")
        session.add(
            ImageAnalysis(
                asset=failed,
                status=AnalysisStatus.FAILED.value,
                ocr_text="金额 200 元",
            )
        )
        session.add(
            ImageAnalysis(
                asset=succeeded,
                status=AnalysisStatus.SUCCEEDED.value,
                ocr_text="金额 300 元",
            )
        )
        session.commit()

        results = search_assets("金额", session=session, asset_filter="failed")

        assert results.total == 1
        assert results.items[0].asset.id == failed.id


class StaticOCRProvider(OCRProvider):
    def __init__(self, text: str) -> None:
        self.text = text

    def extract_text(self, image_path: Path) -> OCRResult:
        return OCRResult(text=self.text)


class FailingOCRProvider(OCRProvider):
    def extract_text(self, image_path: Path) -> OCRResult:
        raise RuntimeError("OCR failed")


def scan_sample_asset(tmp_path, *, session: Session) -> ImageAsset:
    image_root = tmp_path / "images"
    thumbnail_root = tmp_path / "thumbnails"
    image_root.mkdir()
    image_path = image_root / "sample.png"
    Image.new("RGB", (24, 16), "green").save(image_path)

    scan_image_directory(image_root, session=session, thumbnail_root=thumbnail_root)
    asset = session.scalar(select(ImageAsset))
    assert asset is not None
    return asset


def add_asset(session: Session, name: str, sha_prefix: str) -> ImageAsset:
    asset = ImageAsset(
        path=f"D:/Pictures/{name}",
        sha256=sha_prefix * 64,
        file_size=100,
    )
    session.add(asset)
    session.flush()
    return asset


@contextmanager
def in_memory_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine, expire_on_commit=False) as session:
        yield session
