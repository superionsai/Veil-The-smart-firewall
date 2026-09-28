from __future__ import annotations

import threading
from collections import deque

from ..models import FrameMetrics


class RuntimeMetrics:
    def __init__(self, window: int = 200):
        self._frames: deque[FrameMetrics] = deque(maxlen=window)
        self._lock = threading.RLock()

    def add(self, metrics: FrameMetrics):
        with self._lock:
            self._frames.append(metrics)

    def snapshot(self) -> dict:
        with self._lock:
            items = list(self._frames)
        if not items:
            return {
                "frames": 0,
                "avg_total_ms": 0.0,
                "avg_ocr_ms": 0.0,
                "avg_semantic_ms": 0.0,
                "skip_rate": 0.0,
                "avg_regions": 0.0,
                "semantic_calls": 0,
            }
        n = len(items)
        return {
            "frames": n,
            "avg_total_ms": round(sum(x.total_ms for x in items) / n, 2),
            "avg_ocr_ms": round(sum(x.ocr_ms for x in items) / n, 2),
            "avg_semantic_ms": round(sum(x.semantic_ms for x in items) / n, 2),
            "skip_rate": round(sum(1 for x in items if x.skipped) / n, 4),
            "avg_changed_fraction": round(sum(x.changed_fraction for x in items) / n, 4),
            "avg_regions": round(sum(x.regions for x in items) / n, 2),
            "semantic_calls": sum(x.semantic_calls for x in items),
        }
