from __future__ import annotations

import io
import uuid
from pathlib import Path

import fitz
from PIL import Image

from ..models import Policy, PrivacyRegion
from .frame_processor import FrameProcessor
from .redaction import redact_image


class FileSanitizer:
    def __init__(self, output_dir: Path, processor_factory):
        self.output_dir = output_dir
        self.processor_factory = processor_factory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def sanitize(self, filename: str, content: bytes, policy: Policy) -> dict:
        suffix = Path(filename or "upload").suffix.lower()
        if suffix == ".pdf":
            return self._sanitize_pdf(filename, content, policy)
        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            return self._sanitize_image(filename, content, policy)
        raise ValueError("Unsupported file type. Use PDF, PNG, JPG, JPEG, WEBP or BMP.")

    def _sanitize_image(self, filename: str, content: bytes, policy: Policy) -> dict:
        try:
            image = Image.open(io.BytesIO(content)).convert("RGB")
        except Exception as exc:
            raise ValueError("Could not decode uploaded image") from exc
        processor: FrameProcessor = self.processor_factory(session_prefix="file")
        result = processor.process(image, policy, force_full=True)
        regions = _regions_from_public(result.regions)
        redacted = redact_image(image, regions)
        out_name = f"veil-{uuid.uuid4().hex[:10]}-{Path(filename).stem}.png"
        out_path = self.output_dir / out_name
        redacted.save(out_path, format="PNG", optimize=True)
        return {
            "kind": "image",
            "download_url": f"/outputs/{out_name}",
            "output_name": out_name,
            "detections": result.regions,
            "count": len(result.regions),
            "preview_url": f"/outputs/{out_name}",
            "metrics": result.metrics.model_dump(),
        }

    def _sanitize_pdf(self, filename: str, content: bytes, policy: Policy) -> dict:
        source = fitz.open(stream=content, filetype="pdf")
        target = fitz.open()
        all_detections = []
        try:
            for page_number, page in enumerate(source):
                # Fresh processor per page prevents temporal masks from one page
                # leaking onto the next page.
                processor: FrameProcessor = self.processor_factory(session_prefix="pdf")
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                mode = "RGB" if pix.n == 3 else "RGBA"
                image = Image.frombytes(mode, (pix.width, pix.height), pix.samples).convert("RGB")
                result = processor.process(image, policy, force_full=True)
                regions = _regions_from_public(result.regions)
                redacted = redact_image(image, regions)
                png = io.BytesIO()
                redacted.save(png, format="PNG", optimize=True)
                rect = page.rect
                new_page = target.new_page(width=rect.width, height=rect.height)
                new_page.insert_image(new_page.rect, stream=png.getvalue())
                for d in result.regions:
                    item = dict(d)
                    item["page"] = page_number + 1
                    all_detections.append(item)

            out_name = f"veil-{uuid.uuid4().hex[:10]}-{Path(filename).stem}.pdf"
            out_path = self.output_dir / out_name
            target.save(out_path, garbage=4, deflate=True)
        finally:
            target.close()
            source.close()
        return {
            "kind": "pdf",
            "download_url": f"/outputs/{out_name}",
            "output_name": out_name,
            "detections": all_detections,
            "count": len(all_detections),
            "preview_data_url": None,
            "note": "Protected PDF is intentionally rasterized so hidden pixels/text cannot be recovered by selecting or copying the original PDF text layer.",
        }


def _regions_from_public(items: list[dict]) -> list[PrivacyRegion]:
    from ..models import Box, PrivacyCategory, PrivacyAction

    out = []
    for item in items:
        pb = item["pixel_box"]
        out.append(PrivacyRegion(
            box=Box(**pb),
            category=PrivacyCategory(item["category"]),
            confidence=float(item["confidence"]),
            source=item["source"],
            action=PrivacyAction(item["action"]),
            replacement=item.get("replacement"),
            reason=item.get("reason"),
        ))
    return out
