from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "smart_gallery_ai",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

