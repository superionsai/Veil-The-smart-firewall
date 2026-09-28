from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..models import PrivacyAction, PrivacyRegion


def redact_image(image: Image.Image, regions: list[PrivacyRegion]) -> Image.Image:
    out = image.convert("RGB").copy()
    w, h = out.size
    draw = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except Exception:
        font = ImageFont.load_default()

    for region in regions:
        box = region.box.clamp(w, h)
        if box.w <= 0 or box.h <= 0:
            continue
        rect = (box.x, box.y, box.x2, box.y2)
        if region.action == PrivacyAction.WARN:
            draw.rectangle(rect, outline=(255, 191, 0), width=2)
            continue
        if region.action == PrivacyAction.ALLOW:
            continue
        if region.action == PrivacyAction.BLUR:
            roi = out.crop(rect)
            radius = max(3.0, min(box.w, box.h) / 7.0)
            roi = roi.filter(ImageFilter.GaussianBlur(radius=radius))
            out.paste(roi, (box.x, box.y))
            draw = ImageDraw.Draw(out)
            continue
        # BLOCK and REPLACE are burned in. REPLACE uses a generic marker to
        # avoid re-exposing data inside the protected output.
        draw.rectangle(rect, fill=(24, 24, 28))
        label = region.replacement or f"[{region.category.value.replace('_', ' ')}]"
        if box.h >= 18 and box.w >= 60:
            draw.text((box.x + 4, box.y + 3), label[:26], fill=(238, 238, 242), font=font)
    return out
