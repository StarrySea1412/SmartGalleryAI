from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float | None = None


@dataclass(frozen=True)
class CaptionResult:
    caption: str
    labels: list[str]
    model: str


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    model: str


class OCRProvider(ABC):
    @abstractmethod
    def extract_text(self, image_path: Path) -> OCRResult:
        raise NotImplementedError


class CaptionProvider(ABC):
    @abstractmethod
    def describe(self, image_path: Path) -> CaptionResult:
        raise NotImplementedError


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_image(self, image_path: Path) -> EmbeddingResult:
        raise NotImplementedError

