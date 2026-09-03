"""Initial schema.

Revision ID: 202606190001
Revises:
Create Date: 2026-06-19 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202606190001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "image_assets" not in tables:
        op.create_table(
            "image_assets",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("path", sa.Text(), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("mime_type", sa.String(length=128), nullable=True),
            sa.Column("file_size", sa.BigInteger(), nullable=False),
            sa.Column("width", sa.Integer(), nullable=True),
            sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("thumbnail_path", sa.Text(), nullable=True),
            sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("sha256", name="uq_image_assets_sha256"),
        )
        op.create_index("ix_image_assets_path", "image_assets", ["path"], unique=True)
        op.create_index("ix_image_assets_sha256", "image_assets", ["sha256"], unique=False)
    else:
        image_asset_columns = column_names("image_assets")
        if "thumbnail_path" not in image_asset_columns:
            op.add_column("image_assets", sa.Column("thumbnail_path", sa.Text(), nullable=True))
        if "last_scanned_at" not in image_asset_columns:
            op.add_column(
                "image_assets",
                sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
            )
            op.execute(
                "UPDATE image_assets "
                "SET last_scanned_at = COALESCE(updated_at, imported_at, CURRENT_TIMESTAMP)"
            )

    if "image_analyses" not in tables:
        op.create_table(
            "image_analyses",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("asset_id", sa.String(length=36), nullable=False),
            sa.Column("caption", sa.Text(), nullable=True),
            sa.Column("ocr_text", sa.Text(), nullable=True),
            sa.Column("labels", sa.JSON(), nullable=True),
            sa.Column("dominant_colors", sa.JSON(), nullable=True),
            sa.Column(
                "status",
                sa.String(length=32),
                server_default="pending",
                nullable=False,
            ),
            sa.Column("provider", sa.String(length=128), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("embedding_model", sa.String(length=128), nullable=True),
            sa.Column("embedding", sa.JSON(), nullable=True),
            sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["asset_id"], ["image_assets.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("asset_id"),
        )
    else:
        image_analysis_columns = column_names("image_analyses")
        if "status" not in image_analysis_columns:
            op.add_column(
                "image_analyses",
                sa.Column(
                    "status",
                    sa.String(length=32),
                    server_default="pending",
                    nullable=False,
                ),
            )
        if "provider" not in image_analysis_columns:
            op.add_column(
                "image_analyses",
                sa.Column("provider", sa.String(length=128), nullable=True),
            )
        if "error_message" not in image_analysis_columns:
            op.add_column(
                "image_analyses",
                sa.Column("error_message", sa.Text(), nullable=True),
            )
        if "duration_ms" not in image_analysis_columns:
            op.add_column(
                "image_analyses",
                sa.Column("duration_ms", sa.Integer(), nullable=True),
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "image_analyses" in tables:
        op.drop_table("image_analyses")
    if "image_assets" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("image_assets")}
        if "ix_image_assets_sha256" in indexes:
            op.drop_index("ix_image_assets_sha256", table_name="image_assets")
        if "ix_image_assets_path" in indexes:
            op.drop_index("ix_image_assets_path", table_name="image_assets")
        op.drop_table("image_assets")


def column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}
