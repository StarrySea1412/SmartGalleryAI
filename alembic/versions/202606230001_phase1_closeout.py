"""Phase 1 closeout indexes.

Revision ID: 202606230001
Revises: 202606190001
Create Date: 2026-06-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202606230001"
down_revision: str | None = "202606190001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("image_assets")}

    if "ix_image_assets_imported_at" not in indexes:
        op.create_index(
            "ix_image_assets_imported_at",
            "image_assets",
            ["imported_at"],
            unique=False,
        )

    if bind.dialect.name == "sqlite":
        op.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS image_search_fts "
            "USING fts5(asset_id UNINDEXED, path, ocr_text, caption, labels)"
        )
        op.execute("DELETE FROM image_search_fts")
        op.execute(
            "INSERT INTO image_search_fts (asset_id, path, ocr_text, caption, labels) "
            "SELECT image_assets.id, image_assets.path, "
            "COALESCE(image_analyses.ocr_text, ''), "
            "COALESCE(image_analyses.caption, ''), "
            "COALESCE(CAST(image_analyses.labels AS TEXT), '') "
            "FROM image_assets "
            "LEFT JOIN image_analyses ON image_analyses.asset_id = image_assets.id"
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if bind.dialect.name == "sqlite":
        op.execute("DROP TABLE IF EXISTS image_search_fts")

    indexes = {index["name"] for index in inspector.get_indexes("image_assets")}
    if "ix_image_assets_imported_at" in indexes:
        op.drop_index("ix_image_assets_imported_at", table_name="image_assets")

