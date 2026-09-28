from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from veil.config import settings
from veil.core.file_sanitizer import FileSanitizer
from veil.core.frame_processor import FrameProcessor
from veil.inference.heuristic import HeuristicProvider
from veil.inference.semantic import SemanticService
from veil.metrics import AuditStore, RuntimeMetrics
from veil.models import Box, OCRBlock
from veil.ocr.base import OCRProvider
from veil.policy import get_policy


class FixedOCR(OCRProvider):
    name = "fixed"
    def available(self): return True
    def extract(self, image):
        return [OCRBlock(text="OPENAI_KEY=sk-THIS_IS_A_FAKE_DEMO_TOKEN_123456789", box=Box(x=10, y=10, w=360, h=30), confidence=1.0)]


def test_image_sanitizer_burns_in_mask(tmp_path: Path):
    img = Image.new("RGB", (420, 80), "white")
    ImageDraw.Draw(img).text((10, 10), "OPENAI_KEY=sk-THIS_IS_A_FAKE_DEMO_TOKEN_123456789", fill="black")
    raw = BytesIO(); img.save(raw, format="PNG")

    semantic = SemanticService(HeuristicProvider())
    audit = AuditStore(tmp_path / "audit.db", enabled=False)
    runtime = RuntimeMetrics()
    def factory(session_prefix="file"):
        return FrameProcessor(settings, FixedOCR(), semantic, audit, runtime, session_id=session_prefix)

    sanitizer = FileSanitizer(tmp_path / "out", factory)
    result = sanitizer.sanitize("demo.png", raw.getvalue(), get_policy("external"))
    assert result["count"] >= 1
    out = Image.open(tmp_path / "out" / result["output_name"]).convert("RGB")
    # Block redaction uses a dark fill over the sensitive line.
    px = out.getpixel((20, 20))
    assert max(px) < 80
