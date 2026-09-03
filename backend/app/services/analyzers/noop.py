from pathlib import Path

from app.services.analyzers.base import (
    CaptionProvider,
    CaptionResult,
    EmbeddingProvider,
    EmbeddingResult,
    OCRProvider,
    OCRResult,
)


class NoopOCRProvider(OCRProvider):
    def extract_text(self, image_path: Path) -> OCRResult:
        return OCRResult(text="")


class NoopCaptionProvider(CaptionProvider):
    def describe(self, image_path: Path) -> CaptionResult:
        return CaptionResult(caption="", labels=[], model="noop")


class NoopEmbeddingProvider(EmbeddingProvider):
    def embed_image(self, image_path: Path) -> EmbeddingResult:
        return EmbeddingResult(vector=[], model="noop")
