from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.image_asset import ImageAsset

SEARCH_INDEX_TABLE = "image_search_fts"


class SearchIndexUnavailable(RuntimeError):
    pass


def is_sqlite_session(session: Session) -> bool:
    bind = session.get_bind()
    return bind.dialect.name == "sqlite"


def search_index_asset_ids(session: Session, query: str, *, limit: int = 5000) -> list[str]:
    if not is_sqlite_session(session):
        return []

    try:
        rows = session.execute(
            text(
                "SELECT asset_id FROM image_search_fts "
                "WHERE image_search_fts MATCH :query "
                "LIMIT :limit"
            ),
            {"query": quote_fts_query(query), "limit": limit},
        )
        return [str(row[0]) for row in rows]
    except SQLAlchemyError:
        session.rollback()
        return []


def upsert_search_index(session: Session, asset: ImageAsset) -> None:
    if not is_sqlite_session(session):
        raise SearchIndexUnavailable("Search index is only supported for SQLite")

    analysis = asset.analysis
    labels = " ".join(analysis.labels or []) if analysis is not None else ""

    try:
        session.execute(
            text("DELETE FROM image_search_fts WHERE asset_id = :asset_id"),
            {"asset_id": asset.id},
        )
        session.execute(
            text(
                "INSERT INTO image_search_fts "
                "(asset_id, path, ocr_text, caption, labels) "
                "VALUES (:asset_id, :path, :ocr_text, :caption, :labels)"
            ),
            {
                "asset_id": asset.id,
                "path": asset.path,
                "ocr_text": (analysis.ocr_text if analysis is not None else "") or "",
                "caption": (analysis.caption if analysis is not None else "") or "",
                "labels": labels,
            },
        )
    except SQLAlchemyError as exc:
        raise SearchIndexUnavailable("Search index is not available") from exc


def rebuild_search_index(session: Session, assets: list[ImageAsset]) -> int:
    if not is_sqlite_session(session):
        raise SearchIndexUnavailable("Search index is only supported for SQLite")

    try:
        session.execute(text("DELETE FROM image_search_fts"))
        for asset in assets:
            upsert_search_index(session, asset)
    except (SQLAlchemyError, SearchIndexUnavailable) as exc:
        raise SearchIndexUnavailable("Search index is not available") from exc

    return len(assets)


def sync_asset_search_index(session: Session, asset: ImageAsset) -> None:
    try:
        upsert_search_index(session, asset)
        session.commit()
    except SearchIndexUnavailable:
        session.rollback()


def quote_fts_query(query: str) -> str:
    escaped = query.strip().replace('"', '""')
    return f'"{escaped}"'
