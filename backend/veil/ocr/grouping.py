from __future__ import annotations

from ..geometry import union_box
from ..models import OCRBlock
from ..utils import compact_space


def group_words_into_lines(blocks: list[OCRBlock], y_tolerance: float = 0.65, gap_factor: float = 2.5) -> list[OCRBlock]:
    """Merge OCR word boxes into line-like semantic chunks."""
    if not blocks:
        return []
    blocks = sorted(blocks, key=lambda b: (b.box.y, b.box.x))
    lines: list[list[OCRBlock]] = []

    for block in blocks:
        placed = False
        cy = block.box.y + block.box.h / 2
        for line in reversed(lines[-5:]):
            heights = [max(1, b.box.h) for b in line]
            avg_h = sum(heights) / len(heights)
            line_cy = sum(b.box.y + b.box.h / 2 for b in line) / len(line)
            if abs(cy - line_cy) > max(avg_h, block.box.h) * y_tolerance:
                continue
            rightmost = max(line, key=lambda b: b.box.x2)
            gap = block.box.x - rightmost.box.x2
            if gap <= max(avg_h, block.box.h) * gap_factor:
                line.append(block)
                placed = True
                break
        if not placed:
            lines.append([block])

    grouped: list[OCRBlock] = []
    for line in lines:
        line = sorted(line, key=lambda b: b.box.x)
        text = compact_space(" ".join(b.text for b in line))
        if not text:
            continue
        grouped.append(
            OCRBlock(
                text=text,
                box=union_box([b.box for b in line]),
                confidence=sum(b.confidence for b in line) / len(line),
            )
        )
    return grouped
