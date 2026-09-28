from __future__ import annotations

import numpy as np
from PIL import Image

from ..models import Box, OCRBlock
from .base import OCRProvider


class RapidOCROCR(OCRProvider):
    name = "rapidocr"

    def __init__(self, min_confidence: float = 0.35):
        self.min_confidence = min_confidence
        self._engine = None

    def available(self) -> bool:
        try:
            from rapidocr_onnxruntime import RapidOCR  # noqa: F401
            return True
        except Exception:
            return False

    def _get_engine(self):
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
        return self._engine

    def extract(self, image: Image.Image) -> list[OCRBlock]:
        if image.width <= 0 or image.height <= 0:
            return []
        engine = self._get_engine()
        # RapidOCR accepts an ndarray. RGB is used here so the core project stays
        # Pillow-native; current RapidOCR releases normalize internally.
        array = np.asarray(image.convert("RGB"))
        result, _ = engine(array)
        blocks: list[OCRBlock] = []
        if not result:
            return blocks
        for item in result:
            points, text, score = item[0], str(item[1]), float(item[2])
            if score < self.min_confidence or not text.strip():
                continue
            xs = [float(p[0]) for p in points]
            ys = [float(p[1]) for p in points]
            x1, x2 = int(min(xs)), int(max(xs))
            y1, y2 = int(min(ys)), int(max(ys))
            blocks.append(OCRBlock(
                text=text.strip(),
                confidence=max(0.0, min(1.0, score)),
                box=Box(x=x1, y=y1, w=max(1, x2 - x1), h=max(1, y2 - y1)),
            ))
        return blocks
