from __future__ import annotations

from collections import deque

import numpy as np
from PIL import Image

from ..models import Box


class TileChangeDetector:
    """Detect changed screen regions without OpenCV.

    The implementation intentionally uses only Pillow + NumPy so the native
    Snapdragon/Windows ARM64 path does not depend on third-party OpenCV wheels.
    """

    def __init__(self, tile_size: int = 128, mean_threshold: float = 8.0, padding: int = 24):
        self.tile_size = max(32, tile_size)
        self.mean_threshold = mean_threshold
        self.padding = padding
        self.previous_gray: np.ndarray | None = None

    def detect(self, image: Image.Image) -> tuple[list[Box], float]:
        rgb = image.convert("RGB")
        w, h = rgb.size
        gray = np.asarray(rgb.convert("L"), dtype=np.int16)
        if self.previous_gray is None or self.previous_gray.shape != gray.shape:
            self.previous_gray = gray
            return [Box(x=0, y=0, w=w, h=h)], 1.0

        diff = np.abs(gray - self.previous_gray)
        self.previous_gray = gray

        rows = (h + self.tile_size - 1) // self.tile_size
        cols = (w + self.tile_size - 1) // self.tile_size
        mask = np.zeros((rows, cols), dtype=bool)
        changed_pixels = 0

        for r in range(rows):
            y1 = r * self.tile_size
            y2 = min(h, y1 + self.tile_size)
            for c in range(cols):
                x1 = c * self.tile_size
                x2 = min(w, x1 + self.tile_size)
                tile = diff[y1:y2, x1:x2]
                score = float(tile.mean()) if tile.size else 0.0
                if score >= self.mean_threshold:
                    mask[r, c] = True
                    changed_pixels += (y2 - y1) * (x2 - x1)

        fraction = changed_pixels / max(1, w * h)
        if not mask.any():
            return [], 0.0

        boxes = self._components_to_boxes(mask, w, h)
        # Keep runtime bounded during animations/video: merge many components
        # into one screen-sized OCR pass.
        if len(boxes) > 12 or fraction > 0.72:
            return [Box(x=0, y=0, w=w, h=h)], fraction
        return boxes, fraction

    def _components_to_boxes(self, mask: np.ndarray, width: int, height: int) -> list[Box]:
        rows, cols = mask.shape
        visited = np.zeros_like(mask, dtype=bool)
        boxes: list[Box] = []
        neighbors = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0), (1, 1),
        ]

        for r0 in range(rows):
            for c0 in range(cols):
                if not mask[r0, c0] or visited[r0, c0]:
                    continue
                q = deque([(r0, c0)])
                visited[r0, c0] = True
                min_r = max_r = r0
                min_c = max_c = c0
                while q:
                    r, c = q.popleft()
                    min_r, max_r = min(min_r, r), max(max_r, r)
                    min_c, max_c = min(min_c, c), max(max_c, c)
                    for dr, dc in neighbors:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and mask[nr, nc] and not visited[nr, nc]:
                            visited[nr, nc] = True
                            q.append((nr, nc))

                x1 = max(0, min_c * self.tile_size - self.padding)
                y1 = max(0, min_r * self.tile_size - self.padding)
                x2 = min(width, (max_c + 1) * self.tile_size + self.padding)
                y2 = min(height, (max_r + 1) * self.tile_size + self.padding)
                boxes.append(Box(x=x1, y=y1, w=max(1, x2 - x1), h=max(1, y2 - y1)))
        return boxes
