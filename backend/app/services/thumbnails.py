from pathlib import Path

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:
    Image = None
    ImageOps = None
    UnidentifiedImageError = OSError

DEFAULT_THUMBNAIL_SIZE = (512, 512)


class ThumbnailGenerationError(RuntimeError):
    pass


def thumbnail_path_for(sha256: str, thumbnail_root: Path) -> Path:
    return (thumbnail_root / sha256[:2] / f"{sha256}.webp").resolve()


def generate_thumbnail(
    source_path: Path,
    *,
    sha256: str,
    thumbnail_root: Path,
    size: tuple[int, int] = DEFAULT_THUMBNAIL_SIZE,
) -> Path:
    target_path = thumbnail_path_for(sha256, thumbnail_root)
    if target_path.exists():
        return target_path

    if Image is None or ImageOps is None:
        raise ThumbnailGenerationError(
            'Pillow is not installed. Install with: pip install -e ".[dev]"'
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with Image.open(source_path) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail(size)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGB")
            image.save(target_path, format="WEBP", quality=82, method=6)
    except (OSError, UnidentifiedImageError) as exc:
        raise ThumbnailGenerationError(f"Could not generate thumbnail: {source_path}") from exc

    return target_path
