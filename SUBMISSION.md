# Submission Draft

## Title

**Veil — On-Device Semantic Privacy Firewall for AI PCs**

## One-line summary

Veil prevents accidental information leakage during live screen sharing and file sharing by combining local OCR, deterministic secret detection, semantic privacy classification and user-defined privacy policies on a Snapdragon-powered PC.

## Problem

Modern work frequently involves sharing screens, screenshots, logs, PDFs and documents. Sensitive information can appear incidentally: API tokens in a terminal, a private salary message, an internal project codename, a bank identifier, a QR code or a personal address. Pattern-only redaction cannot capture context, while cloud AI introduces a privacy contradiction: sensitive content has to leave the device before the system can decide whether it should have left the device.

## Solution

Veil creates a protected sharing surface. The user selects a source window and Veil produces a sanitized preview intended to be shared in a meeting. It also generates protected copies of images/PDFs and sanitizes pasted text.

The pipeline is event-driven:

1. detect changed screen tiles,
2. OCR only changed regions,
3. run deterministic secret/identity/financial detectors,
4. send only ambiguous OCR text to a local semantic model,
5. apply a user-selected or natural-language-compiled privacy policy,
6. persist masks over unchanged areas,
7. render/export the protected result.

## Technical implementation

- FastAPI + WebSocket local server.
- Browser permission-based screen capture.
- OpenCV-free Pillow/NumPy tile-difference change detector for Windows ARM64 portability.
- Pluggable local OCR layer.
- Pattern detectors + Luhn/Verhoeff validation.
- Local semantic classification via Qualcomm GenieX provider interface.
- Snapdragon QAIRT/NPU target using `Qwen3-4B-Instruct-2507` where supported.
- Batched semantic classification and LRU-style cache.
- Natural-language policy compiler.
- Browser-native live QR detection where supported; optional OpenCV server-side QR/face detection on compatible platforms.
- Privacy-preserving SQLite audit metadata.
- PDF raster redaction to remove recoverable text layers.

## Innovation

The novelty is not simply PII detection. Veil combines:

- **semantic DLP for ordinary live sharing**,
- **privacy policy compilation from natural language**,
- **confidence-gated model escalation**,
- **event-driven multimodal inference**, and
- **fail-closed protected-frame rendering**.

The local model decides semantics; deterministic/vision components retain geometric grounding.

## Snapdragon relevance

The semantic privacy model processes material that is potentially sensitive by definition. Local inference avoids transmitting that content to a cloud endpoint. GenieX provides a direct/local server interface and QAIRT model path for Snapdragon's NPU, making local acceleration a core architectural requirement rather than a cosmetic optimization.

## Accessibility/deployment

- localhost web app,
- no account required,
- no cloud service required,
- works with ordinary apps because the user shares the Veil protected surface,
- cross-platform fallback permits development/testing without specialized hardware,
- privacy policies are visible and editable instead of being hidden in model prompts.

## Evaluation plan

Report measured values from the target Snapdragon PC for:

- detection precision/recall/F1,
- leak rate,
- overmask rate,
- median/mean protected-frame latency,
- percentage of frames skipped by change detection,
- semantic model calls/minute,
- semantic-only vs cascade vs full event-driven pipeline.

Do not submit placeholder numbers. Use `benchmarks/run_benchmark.py` and capture Diagnostics screenshots from the actual target machine.
