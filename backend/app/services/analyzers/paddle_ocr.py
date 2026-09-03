from pathlib import Path
from typing import Any

from app.services.analyzers.base import OCRProvider, OCRResult


class PaddleOCRProvider(OCRProvider):
    def __init__(self, *, lang: str = "ch") -> None:
        self.lang = lang
        self._ocr: Any | None = None

    def extract_text(self, image_path: Path) -> OCRResult:
        raw_result = self._client.ocr(str(image_path), cls=True)
        lines, confidences = parse_paddle_ocr_result(raw_result)
        confidence = sum(confidences) / len(confidences) if confidences else None
        return OCRResult(text="\n".join(lines), confidence=confidence)

    @property
    def _client(self) -> Any:
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
            except ImportError as exc:
                raise RuntimeError(
                    'PaddleOCR is not installed. Install with: pip install -e ".[ai]"'
                ) from exc

            self._ocr = PaddleOCR(use_angle_cls=True, lang=self.lang)
        return self._ocr


def parse_paddle_ocr_result(raw_result: Any) -> tuple[list[str], list[float]]:
    lines: list[str] = []
    confidences: list[float] = []

    for page in raw_result or []:
        for item in page or []:
            if not isinstance(item, list | tuple) or len(item) < 2:
                continue
            text_info = item[1]
            if not isinstance(text_info, list | tuple) or not text_info:
                continue

            text = str(text_info[0]).strip()
            if not text:
                continue
            lines.append(text)

            if len(text_info) > 1:
                try:
                    confidences.append(float(text_info[1]))
                except (TypeError, ValueError):
                    pass

    return lines, confidences
