from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartGalleryAI"
    env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/smart_gallery.db"
    media_root: Path = Path("./data/media")
    thumbnail_root: Path = Path("./data/thumbnails")
    redis_url: str = "redis://localhost:6379/0"
    ocr_provider: str = "noop"
    enable_cloud_vision: bool = False
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SMART_GALLERY_",
        extra="ignore",
    )

    def ensure_data_dirs(self) -> None:
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.thumbnail_root.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.removeprefix("sqlite:///"))
            db_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
