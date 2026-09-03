from app.core.config import Settings, get_settings
from app.services.analyzers.base import OCRProvider
from app.services.analyzers.noop import NoopOCRProvider
from app.services.analyzers.paddle_ocr import PaddleOCRProvider


def get_ocr_provider(settings: Settings | None = None) -> OCRProvider:
    selected_settings = settings or get_settings()
    provider_name = selected_settings.ocr_provider.strip().lower()

    if provider_name == "noop":
        return NoopOCRProvider()
    if provider_name in {"paddle", "paddleocr"}:
        return PaddleOCRProvider()

    raise ValueError(f"Unsupported OCR provider: {selected_settings.ocr_provider}")
