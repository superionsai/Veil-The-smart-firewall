from __future__ import annotations

import os
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image

from ..geometry import union_box
from ..models import Box, OCRBlock
from .base import OCRProvider


class TesseractOCR(OCRProvider):
    name = "tesseract"

    def __init__(self, min_confidence: float = 0.35, psm: int = 11):
        self.min_confidence = min_confidence
        self.psm = psm
        self._cmd: str | None = None

    def _find_binary(self) -> str | None:
        if self._cmd:
            return self._cmd
        explicit = os.environ.get("TESSERACT_CMD")
        candidates = [
            explicit,
            shutil.which("tesseract"),
            str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Tesseract-OCR" / "tesseract.exe"),
            str(Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Tesseract-OCR" / "tesseract.exe"),
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                self._cmd = str(candidate)
                return self._cmd
        return None

    def available(self) -> bool:
        try:
            import pytesseract
        except Exception:
            return False
        cmd = self._find_binary()
        if not cmd:
            return False
        pytesseract.pytesseract.tesseract_cmd = cmd
        return True

    def extract(self, image: Image.Image) -> list[OCRBlock]:
        """Return Tesseract line blocks rather than individual words."""
        import pytesseract
        from pytesseract import Output

        cmd = self._find_binary()
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        rgb = image.convert("RGB")
        if rgb.width <= 0 or rgb.height <= 0:
            return []
        data = pytesseract.image_to_data(rgb, output_type=Output.DICT, config=f"--psm {self.psm}")

        grouped: dict[tuple[int, int, int], list[tuple[str, float, Box]]] = defaultdict(list)
        n = len(data.get("text", []))
        for i in range(n):
            text = (data["text"][i] or "").strip()
            if not text:
                continue
            try:
                conf_raw = float(data["conf"][i])
            except Exception:
                conf_raw = 0.0
            confidence = max(0.0, min(1.0, conf_raw / 100.0))
            if conf_raw >= 0 and confidence < self.min_confidence:
                continue
            key = (
                int(data.get("block_num", [0] * n)[i]),
                int(data.get("par_num", [0] * n)[i]),
                int(data.get("line_num", [0] * n)[i]),
            )
            grouped[key].append((
                text,
                confidence,
                Box(
                    x=int(data["left"][i]),
                    y=int(data["top"][i]),
                    w=int(data["width"][i]),
                    h=int(data["height"][i]),
                ),
            ))

        lines: list[OCRBlock] = []
        for items in grouped.values():
            items.sort(key=lambda x: x[2].x)
            text = " ".join(x[0] for x in items).strip()
            if not text:
                continue
            lines.append(OCRBlock(
                text=text,
                confidence=sum(x[1] for x in items) / len(items),
                box=union_box([x[2] for x in items]),
            ))
        return sorted(lines, key=lambda b: (b.box.y, b.box.x))
