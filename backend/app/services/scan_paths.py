import os
from pathlib import Path

SCAN_PATH_ALIASES = {
    "image",
    "images",
    "photo",
    "photos",
    "picture",
    "pictures",
    "图库",
    "图片",
    "照片",
    "相册",
}


def resolve_scan_root_path(raw_path: Path) -> Path:
    expanded_path = Path(os.path.expandvars(os.path.expanduser(str(raw_path))))
    if expanded_path.is_dir():
        return expanded_path.resolve()

    if not expanded_path.is_absolute():
        workspace_relative_path = Path.cwd() / expanded_path
        if workspace_relative_path.is_dir():
            return workspace_relative_path.resolve()

    if str(raw_path).strip().lower() in SCAN_PATH_ALIASES:
        known_path = first_existing_known_image_dir()
        if known_path is not None:
            return known_path

    return expanded_path


def get_scan_path_suggestions() -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    seen: set[str] = set()

    for label, path in known_image_dir_candidates():
        if not path.is_dir():
            continue
        resolved = str(path.resolve())
        normalized = resolved.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        suggestions.append({"label": label, "path": resolved})

    return suggestions


def first_existing_known_image_dir() -> Path | None:
    for _, path in known_image_dir_candidates():
        if path.is_dir():
            return path.resolve()
    return None


def known_image_dir_candidates() -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []

    for env_name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        base_path = path_from_env(env_name)
        if base_path is not None:
            candidates.extend(
                [
                    ("OneDrive 图片", base_path / "Pictures"),
                    ("OneDrive 图片", base_path / "图片"),
                ]
            )

    user_profile = path_from_env("USERPROFILE")
    if user_profile is not None:
        candidates.extend(
            [
                ("图片", user_profile / "Pictures"),
                ("图片", user_profile / "图片"),
                ("下载", user_profile / "Downloads"),
                ("下载", user_profile / "下载"),
                ("桌面", user_profile / "Desktop"),
                ("桌面", user_profile / "桌面"),
            ]
        )

    return candidates


def path_from_env(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value)
