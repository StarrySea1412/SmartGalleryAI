from hashlib import sha256
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.image_asset import ImageAsset, utcnow
from app.services.scan_paths import resolve_scan_root_path
from app.services.search_index import sync_asset_search_index
from app.services.thumbnails import ThumbnailGenerationError, generate_thumbnail

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    Image = None
    UnidentifiedImageError = OSError

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def scan_image_directory(
    root_path: Path,
    *,
    session: Session,
    thumbnail_root: Path | None = None,
) -> dict[str, int]:
    root_path = resolve_scan_root_path(root_path)
    if not root_path.exists() or not root_path.is_dir():
        raise ValueError(f"Directory does not exist: {root_path}")

    thumbnail_root = thumbnail_root or get_settings().thumbnail_root
    resolved_thumbnail_root = thumbnail_root.resolve()
    scanned = 0
    imported = 0
    skipped = 0
    indexed_assets: list[ImageAsset] = []

    for path in root_path.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if path.resolve().is_relative_to(resolved_thumbnail_root):
            continue

        scanned += 1
        asset = build_asset(path)
        existing = session.scalar(select(ImageAsset).where(ImageAsset.sha256 == asset.sha256))
        if existing is not None:
            existing.last_scanned_at = utcnow()
            ensure_thumbnail(existing, thumbnail_root=thumbnail_root)
            indexed_assets.append(existing)
            skipped += 1
            continue

        ensure_thumbnail(asset, thumbnail_root=thumbnail_root)
        session.add(asset)
        indexed_assets.append(asset)
        imported += 1

    session.commit()
    for asset in indexed_assets:
        sync_asset_search_index(session, asset)
    return {"scanned": scanned, "imported": imported, "skipped": skipped}


def build_asset(path: Path) -> ImageAsset:
    absolute_path = path.resolve()
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None

    if Image is not None:
        try:
            with Image.open(absolute_path) as image:
                width, height = image.size
                mime_type = Image.MIME.get(image.format)
        except UnidentifiedImageError:
            mime_type = None

    return ImageAsset(
        path=str(absolute_path),
        sha256=file_sha256(absolute_path),
        mime_type=mime_type,
        file_size=absolute_path.stat().st_size,
        width=width,
        height=height,
    )


def ensure_thumbnail(asset: ImageAsset, *, thumbnail_root: Path) -> None:
    try:
        asset.thumbnail_path = str(
            generate_thumbnail(
                Path(asset.path),
                sha256=asset.sha256,
                thumbnail_root=thumbnail_root,
            )
        )
    except ThumbnailGenerationError:
        asset.thumbnail_path = None


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
