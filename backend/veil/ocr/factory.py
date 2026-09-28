from __future__ import annotations

from .base import OCRProvider
from .null import NullOCR
from .rapidocr import RapidOCROCR
from .tesseract import TesseractOCR


def make_ocr_provider(name: str) -> OCRProvider:
    name = (name or "auto").lower()
    providers = {
        "rapidocr": RapidOCROCR,
        "tesseract": TesseractOCR,
        "none": NullOCR,
    }
    if name != "auto":
        cls = providers.get(name)
        if cls is None:
            raise ValueError(f"Unknown OCR provider: {name}")
        provider = cls()
        if not provider.available() and name != "none":
            raise RuntimeError(f"OCR provider '{name}' is not available")
        return provider

    # RapidOCR is self-contained if installed; Tesseract is the broad desktop fallback.
    for cls in (RapidOCROCR, TesseractOCR):
        provider = cls()
        if provider.available():
            return provider
    return NullOCR()
