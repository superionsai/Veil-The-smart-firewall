from __future__ import annotations

import time
from dataclasses import dataclass

from ..geometry import iou
from ..models import Box, PrivacyRegion


@dataclass
class _Tracked:
    region: PrivacyRegion
    last_seen: float


def _intersects(a: Box, b: Box) -> bool:
    return not (a.x2 <= b.x or b.x2 <= a.x or a.y2 <= b.y or b.y2 <= a.y)


class RegionTracker:
    """Persist masks across frames without keeping stale masks after changed content disappears.

    Regions outside all changed areas are assumed unchanged and their lifetime is refreshed.
    Regions inside changed areas must be re-detected; otherwise they expire after ttl_seconds.
    """

    def __init__(self, ttl_seconds: float = 1.2, iou_threshold: float = 0.25):
        self.ttl_seconds = ttl_seconds
        self.iou_threshold = iou_threshold
        self._items: list[_Tracked] = []

    def update(
        self,
        regions: list[PrivacyRegion],
        changed_boxes: list[Box] | None = None,
        now: float | None = None,
    ) -> list[PrivacyRegion]:
        now = now or time.monotonic()
        changed_boxes = changed_boxes or []

        # Static screen areas are still valid even though OCR is intentionally skipped there.
        if changed_boxes:
            for tracked in self._items:
                if not any(_intersects(tracked.region.box, changed) for changed in changed_boxes):
                    tracked.last_seen = now
        else:
            for tracked in self._items:
                tracked.last_seen = now

        for region in regions:
            best = None
            best_iou = 0.0
            for tracked in self._items:
                if tracked.region.category != region.category:
                    continue
                score = iou(tracked.region.box, region.box)
                if score > best_iou:
                    best_iou = score
                    best = tracked
            if best is not None and best_iou >= self.iou_threshold:
                best.region = region
                best.last_seen = now
            else:
                self._items.append(_Tracked(region=region, last_seen=now))

        self._items = [x for x in self._items if now - x.last_seen <= self.ttl_seconds]
        return [x.region for x in self._items]

    def current(self, now: float | None = None) -> list[PrivacyRegion]:
        now = now or time.monotonic()
        self._items = [x for x in self._items if now - x.last_seen <= self.ttl_seconds]
        return [x.region for x in self._items]

    def clear(self) -> None:
        self._items.clear()
