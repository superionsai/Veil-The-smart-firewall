# Veil Architecture

## Design goals

1. Sensitive source content stays local.
2. A live preview must never intentionally render a new raw frame before redaction decisions are available.
3. Expensive semantic inference should be exceptional, not the default per-frame path.
4. Every redaction must be attributable to a detector/policy decision.
5. Qualcomm-specific acceleration must be pluggable rather than infecting the whole application.
6. The same policy engine should govern live video, files, and pasted text.

## Live data path

```text
Browser getDisplayMedia()
        │
        ▼
hidden <video> (source only)
        │ capture JPEG while previous request is idle
        ▼
WebSocket binary frame
        │
        ▼
TileChangeDetector
        │
        ├── no changed tiles ──► reuse temporal masks, no OCR/semantic call
        │
        ▼
changed crops
        │
        ▼
OCRProvider -> OCRBlock(text, pixel box, confidence)
        │
        ▼
line grouping
        │
        ├─────────────► deterministic RegexDetector / validators
        │
        ├─────────────► exact custom-rule matching
        │
        └─────────────► semantic candidate filter
                              │
                              ▼
                    batched SemanticService
                    cache(text+context+rules)
                              │
                              ▼
                    Qwen / GenieX or fallback
        │
        ▼
PolicyEngine
        │
        ▼
VisualDetector (QR / optional face)
        │
        ▼
RegionTracker
        │
        ▼
normalized regions returned to browser
        │
        ▼
Browser draws held ImageBitmap + masks
        │
        ▼
Protected Veil canvas becomes the share target
```

## Why boxes come from OCR, not the LLM

A generative model is poor geometry infrastructure. Veil intentionally separates:

- **where?** → OCR/visual detector bounding box,
- **what?** → deterministic pattern or local semantic classifier,
- **what should happen?** → policy engine.

This makes redactions explainable and prevents the language model from fabricating screen coordinates.

## Event-driven inference

The previous grayscale frame is compared with the current frame in tiles. Tiles whose mean absolute pixel difference crosses a threshold are grouped into connected rectangles and padded. OCR only processes those rectangles.

Static masks are not allowed to expire simply because OCR was skipped. The tracker refreshes masks that lie outside changed rectangles. A mask inside a changed rectangle must be re-detected or it expires after the configured TTL.

This prevents two opposite bugs:

- re-running OCR/LLM on an unchanged secret forever,
- dropping a redaction merely because the optimization skipped unchanged content.

## Semantic cascade

Semantic inference is gated by:

- deterministic detection already fired,
- minimum OCR text length,
- common UI label suppression,
- simple alphanumeric quality check,
- exact custom-rule matching,
- semantic cache,
- batching.

The current provider interface supports:

- `heuristic` — no model, development fallback,
- `geniex_server` — local OpenAI-compatible GenieX endpoint,
- `geniex_direct` — direct GenieX Python API, QAIRT/NPU path.

## Data model

Canonical region:

```python
PrivacyRegion(
    box=Box(x, y, w, h),
    category=PrivacyCategory.AUTH_CREDENTIAL,
    confidence=0.99,
    source="regex:github_token",
    action=PrivacyAction.BLOCK,
    reason="GitHub access token",
)
```

All visual and OCR detectors converge into this structure.

## Privacy policies

A `Policy` contains:

- category → action map,
- exact custom protected concepts,
- allow-list terms,
- semantic enable/disable,
- QR masking flag,
- face masking flag,
- default action.

Actions:

- `ALLOW`
- `BLOCK`
- `BLUR`
- `REPLACE`
- `WARN`

## PDF security choice

The PDF sanitizer renders each source page, detects/masks the rendered pixels, then creates a new PDF from the sanitized page image. This intentionally discards the original text layer, reducing the risk that visually covered text remains extractable.

Trade-off: output PDFs are image-based and may be larger / less accessible. A future production version could rebuild a sanitized text layer from safe OCR output.

## Audit model

The SQLite audit table contains:

- timestamp,
- session id,
- category,
- action,
- detector source,
- confidence,
- SHA-256 of OCR text,
- optional raw text only when `VEIL_RETAIN_RAW_TEXT=1`.

Raw text is off by default.

## Future extensions

These are deliberately outside the challenge MVP but fit the interfaces:

- native Windows capture/virtual display driver,
- QNN/QAIRT OCR provider,
- VLM escalation for non-textual sensitive content,
- organization-managed signed policies,
- browser extension that redirects screen-share sources to Veil,
- safe searchable PDF text-layer reconstruction,
- per-application privacy policy presets,
- active learning from user overrides without uploading content.
