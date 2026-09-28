from __future__ import annotations

import time
import uuid
from typing import Iterable

import io

from PIL import Image

from ..config import Settings
from ..detection import RegexDetector, VisualDetector
from ..inference.semantic import SemanticService
from ..metrics import AuditStore, RuntimeMetrics
from ..models import (
    Box,
    FrameMetrics,
    FrameResult,
    OCRBlock,
    Policy,
    PrivacyCategory,
    PrivacyRegion,
)
from ..ocr.base import OCRProvider
from ..policy import PolicyEngine
from ..tracking import RegionTracker
from ..utils import compact_space
from .change_detection import TileChangeDetector


COMMON_UI = {
    "file", "edit", "view", "help", "window", "terminal", "run", "debug", "settings",
    "save", "open", "close", "cancel", "ok", "yes", "no", "search", "home", "new tab",
    "google chrome", "microsoft edge", "visual studio code", "explorer", "source control",
}


class FrameProcessor:
    def __init__(
        self,
        settings: Settings,
        ocr: OCRProvider,
        semantic: SemanticService,
        audit: AuditStore,
        runtime_metrics: RuntimeMetrics,
        session_id: str | None = None,
    ):
        self.settings = settings
        self.ocr = ocr
        self.semantic = semantic
        self.audit = audit
        self.runtime_metrics = runtime_metrics
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.regex = RegexDetector()
        self.visual = VisualDetector()
        self.policy_engine = PolicyEngine()
        self.tracker = RegionTracker(settings.region_ttl_seconds)
        self.change = TileChangeDetector(
            tile_size=settings.tile_size,
            mean_threshold=settings.change_threshold,
            padding=settings.change_padding,
        )

    def process_bytes(self, encoded_image: bytes, policy: Policy, force_full: bool = False) -> FrameResult:
        try:
            image = Image.open(io.BytesIO(encoded_image)).convert("RGB")
        except Exception as exc:
            raise ValueError("Could not decode image") from exc
        return self.process(image, policy, force_full=force_full)

    def process(self, image: Image.Image, policy: Policy, force_full: bool = False) -> FrameResult:
        if self.ocr.name == "none":
            raise RuntimeError("No OCR backend is available. Configure Tesseract or a compatible RapidOCR backend before protecting visual content.")
        start = time.perf_counter()
        image = image.convert("RGB")
        width, height = image.size
        metrics = FrameMetrics()

        t = time.perf_counter()
        changed_boxes, changed_fraction = self.change.detect(image)
        if force_full:
            changed_boxes = [Box(x=0, y=0, w=width, h=height)]
            changed_fraction = 1.0
        metrics.change_ms = (time.perf_counter() - t) * 1000
        metrics.changed_fraction = changed_fraction

        # No visual change: masks remain valid and no OCR/LLM work is needed.
        if not changed_boxes:
            tracked = self.tracker.update([], changed_boxes=[])
            metrics.skipped = True
            metrics.regions = len(tracked)
            metrics.total_ms = (time.perf_counter() - start) * 1000
            self.runtime_metrics.add(metrics)
            return FrameResult(
                width=width,
                height=height,
                regions=[r.public_dict(width, height, self.settings.retain_raw_text) for r in tracked],
                metrics=metrics,
            )

        t = time.perf_counter()
        grouped = self._ocr_changed_regions(image, changed_boxes)
        metrics.ocr_ms = (time.perf_counter() - t) * 1000
        metrics.ocr_blocks = len(grouped)

        t = time.perf_counter()
        deterministic = self.regex.detect(grouped)
        direct_custom = self._custom_rule_regions(grouped, policy)
        metrics.detection_ms = (time.perf_counter() - t) * 1000

        # Only ambiguous blocks are escalated to the local semantic model.
        sem_candidates = self._semantic_candidates(grouped, deterministic + direct_custom, policy)
        metrics.semantic_candidates = len(sem_candidates)
        semantic_regions: list[PrivacyRegion] = []
        if sem_candidates and policy.semantic_enabled:
            t = time.perf_counter()
            custom_terms = self.policy_engine.custom_terms(policy)
            before_calls = self.semantic.calls
            for batch in _chunks(sem_candidates, self.settings.semantic_batch_size):
                decisions = self.semantic.classify_many(
                    [b.text for b in batch],
                    context=policy.name,
                    custom_terms=custom_terms,
                )
                for block, decision in zip(batch, decisions):
                    if decision.sensitive and decision.category != PrivacyCategory.PUBLIC:
                        semantic_regions.append(
                            PrivacyRegion(
                                box=block.box,
                                text=block.text,
                                category=decision.category,
                                confidence=decision.confidence,
                                source=f"semantic:{self.semantic.provider.name}",
                                reason=decision.reason,
                            )
                        )
            metrics.semantic_ms = (time.perf_counter() - t) * 1000
            metrics.semantic_calls = self.semantic.calls - before_calls

        t = time.perf_counter()
        visual_regions = self.visual.detect(image, mask_qr=policy.mask_qr, mask_faces=policy.mask_faces)
        metrics.visual_ms = (time.perf_counter() - t) * 1000

        combined = deterministic + direct_custom + semantic_regions + visual_regions
        actionable = self.policy_engine.filter_actionable(self._dedupe(combined), policy)
        actionable = [r for r in actionable if r.box.w > 0 and r.box.h > 0][: self.settings.max_regions_per_frame]

        tracked = self.tracker.update(actionable, changed_boxes=changed_boxes)
        metrics.regions = len(tracked)
        metrics.total_ms = (time.perf_counter() - start) * 1000
        self.runtime_metrics.add(metrics)
        self.audit.record(self.session_id, actionable)

        return FrameResult(
            width=width,
            height=height,
            regions=[r.public_dict(width, height, self.settings.retain_raw_text) for r in tracked],
            metrics=metrics,
        )

    def _ocr_changed_regions(self, image: Image.Image, boxes: list[Box]) -> list[OCRBlock]:
        w, h = image.size
        out: list[OCRBlock] = []
        for box in boxes:
            box = box.clamp(w, h)
            crop = image.crop((box.x, box.y, box.x2, box.y2))
            for block in self.ocr.extract(crop):
                out.append(
                    OCRBlock(
                        text=block.text,
                        confidence=block.confidence,
                        box=Box(
                            x=block.box.x + box.x,
                            y=block.box.y + box.y,
                            w=block.box.w,
                            h=block.box.h,
                        ).clamp(w, h),
                    )
                )
        return out

    def _custom_rule_regions(self, blocks: list[OCRBlock], policy: Policy) -> list[PrivacyRegion]:
        out = []
        for block in blocks:
            lower = block.text.lower()
            for rule in policy.custom_rules:
                if rule.concept.strip() and rule.concept.lower() in lower:
                    out.append(
                        PrivacyRegion(
                            box=block.box,
                            text=block.text,
                            category=PrivacyCategory.CUSTOM,
                            confidence=0.99,
                            source="policy:custom_term",
                            action=rule.action,
                            reason=f"Matches protected concept: {rule.concept}",
                        )
                    )
                    break
        return out

    def _semantic_candidates(self, blocks: list[OCRBlock], already: list[PrivacyRegion], policy: Policy) -> list[OCRBlock]:
        protected_boxes = {(r.box.x, r.box.y, r.box.w, r.box.h) for r in already}
        out = []
        for block in blocks:
            text = compact_space(block.text)
            if len(text) < self.settings.semantic_min_chars:
                continue
            if text.lower() in COMMON_UI:
                continue
            if (block.box.x, block.box.y, block.box.w, block.box.h) in protected_boxes:
                continue
            # Avoid spending LLM calls on punctuation/mostly numeric fragments unless a custom concept exists.
            alnum = sum(c.isalnum() for c in text)
            if alnum < max(4, len(text) * 0.35):
                continue
            out.append(block)
        return out

    @staticmethod
    def _dedupe(regions: list[PrivacyRegion]) -> list[PrivacyRegion]:
        best: dict[tuple, PrivacyRegion] = {}
        for r in regions:
            key = (r.box.x, r.box.y, r.box.w, r.box.h, r.category.value)
            if key not in best or r.confidence > best[key].confidence:
                best[key] = r
        return list(best.values())


def _chunks(items: list, size: int) -> Iterable[list]:
    size = max(1, size)
    for i in range(0, len(items), size):
        yield items[i : i + size]
