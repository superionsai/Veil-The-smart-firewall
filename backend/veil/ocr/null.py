from __future__ import annotations

from PIL import Image

from ..models import OCRBlock
from .base import OCRProvider


class NullOCR(OCRProvider):
    name = "none"

    def available(self) -> bool:
        return True

    def extract(self, image: Image.Image) -> list[OCRBlock]:
        return []
