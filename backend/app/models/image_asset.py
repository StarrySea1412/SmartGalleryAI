from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ImageAsset(Base):
    __tablename__ = "image_assets"
    __table_args__ = (UniqueConstraint("sha256", name="uq_image_assets_sha256"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    path: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    thumbnail_path: Mapped[str | None] = mapped_column(Text)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    analysis: Mapped["ImageAnalysis | None"] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ImageAnalysis(Base):
    __tablename__ = "image_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("image_assets.id"),
        unique=True,
        nullable=False,
    )
    caption: Mapped[str | None] = mapped_column(Text)
    ocr_text: Mapped[str | None] = mapped_column(Text)
    labels: Mapped[list[str] | None] = mapped_column(JSON)
    dominant_colors: Mapped[list[str] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AnalysisStatus.PENDING.value,
    )
    provider: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    asset: Mapped[ImageAsset] = relationship(back_populates="analysis")
