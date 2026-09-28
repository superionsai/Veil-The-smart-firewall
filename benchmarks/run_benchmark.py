from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from veil.config import settings  # noqa: E402
from veil.core.frame_processor import FrameProcessor  # noqa: E402
from veil.core.text_sanitizer import TextSanitizer  # noqa: E402
from veil.inference.factory import make_semantic_provider  # noqa: E402
from veil.inference.heuristic import HeuristicProvider  # noqa: E402
from veil.inference.semantic import SemanticService  # noqa: E402
from veil.metrics import AuditStore, RuntimeMetrics  # noqa: E402
from veil.ocr import make_ocr_provider  # noqa: E402
from veil.policy import get_policy  # noqa: E402


def dataset() -> list[dict]:
    sensitive = [
        ("OPENAI_KEY=sk-THIS_IS_A_FAKE_DEMO_TOKEN_123456789", "AUTH_CREDENTIAL"),
        ("GITHUB_TOKEN=ghp_FAKEDEMO1234567890123456789012", "AUTH_CREDENTIAL"),
        ("Authorization: Bearer fake_demo_token_ABCDEFGHIJKLMNOPQRSTUVWXYZ", "AUTH_CREDENTIAL"),
        ("DATABASE_URL=postgres://demo:fakepassword@localhost:5432/db", "AUTH_CREDENTIAL"),
        ("Contact me at person42@example.com", "CONTACT"),
        ("My phone is 9876543210", "CONTACT"),
        ("PAN: ABCDE1234F", "IDENTITY"),
        ("IFSC SBIN0001234", "FINANCIAL"),
        ("Payment handle demo-user@paytm", "FINANCIAL"),
        ("Project Orion acquisition estimate is confidential.", "CONFIDENTIAL_WORK"),
        ("Candidate salary offer ₹21 LPA approved; do not share.", "CONFIDENTIAL_WORK"),
        ("Internal only: unreleased product roadmap for Q4.", "CONFIDENTIAL_WORK"),
        ("Please don't tell anyone about the private board meeting.", "PRIVATE_COMMUNICATION"),
        ("Patient diagnosis and prescription are attached.", "HEALTH"),
        ("My residential address should remain private.", "LOCATION"),
    ]
    safe = [
        "Meeting moved to Friday.",
        "Build completed successfully.",
        "Documentation updated.",
        "localhost:8080 is running.",
        "The API_KEY variable is documented here without a value.",
        "Use a strong password in production.",
        "Project planning meeting begins at 10 AM.",
        "Public release notes are available.",
        "File Edit View Terminal Run Help",
        "The card component should have rounded corners.",
        "Email is a communication protocol.",
        "Financial literacy workshop starts tomorrow.",
        "Health checks passed for all services.",
        "Location services are disabled in this demo.",
        "A JWT has three dot-separated segments.",
    ]
    rows = []
    # Repeat with harmless prefixes/suffixes to create a larger deterministic benchmark.
    for rep in range(5):
        for text, cat in sensitive:
            rows.append({"text": f"[{rep}] {text}", "sensitive": True, "category": cat})
        for text in safe:
            rows.append({"text": f"[{rep}] {text}", "sensitive": False, "category": "PUBLIC"})
    return rows


def score(y_true, y_pred):
    tp = sum(t and p for t, p in zip(y_true, y_pred))
    tn = sum((not t) and (not p) for t, p in zip(y_true, y_pred))
    fp = sum((not t) and p for t, p in zip(y_true, y_pred))
    fn = sum(t and (not p) for t, p in zip(y_true, y_pred))
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "leak_rate": fn / max(1, tp + fn),
        "overmask_rate": fp / max(1, tn + fp),
    }


def run_text(use_configured_provider: bool):
    provider = make_semantic_provider(settings) if use_configured_provider else HeuristicProvider()
    semantic = SemanticService(provider)
    sanitizer = TextSanitizer(semantic)
    policy = get_policy("external")
    rows = dataset()
    preds, times = [], []
    for row in rows:
        start = time.perf_counter()
        _safe, detections = sanitizer.sanitize(row["text"], policy)
        times.append((time.perf_counter() - start) * 1000)
        preds.append(bool(detections))
    result = score([r["sensitive"] for r in rows], preds)
    result.update({
        "mode": "text",
        "samples": len(rows),
        "provider": provider.name,
        "semantic_provider_calls": semantic.calls,
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "p95_ms": sorted(times)[max(0, int(len(times) * .95) - 1)],
    })
    return result


def render_text_image(text: str):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1200, 180), "white")
    draw = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", 32)
    except Exception:
        f = ImageFont.load_default()
    draw.text((28, 60), text, fill="black", font=f)
    return img


def run_image(use_configured_provider: bool, limit: int):
    provider = make_semantic_provider(settings) if use_configured_provider else HeuristicProvider()
    semantic = SemanticService(provider)
    ocr = make_ocr_provider(settings.ocr_provider)
    if ocr.name == "none":
        raise RuntimeError("No OCR engine is available. Install Tesseract/RapidOCR or set VEIL_OCR_PROVIDER.")
    runtime = RuntimeMetrics()
    tmp = Path(tempfile.mkdtemp()) / "bench.db"
    audit = AuditStore(tmp, enabled=False)
    policy = get_policy("external")
    rows = dataset()[:limit]
    preds, times = [], []
    for row in rows:
        proc = FrameProcessor(settings, ocr, semantic, audit, runtime, session_id="bench")
        frame = render_text_image(row["text"])
        start = time.perf_counter()
        result = proc.process(frame, policy, force_full=True)
        times.append((time.perf_counter() - start) * 1000)
        preds.append(bool(result.regions))
    result = score([r["sensitive"] for r in rows], preds)
    result.update({
        "mode": "image",
        "samples": len(rows),
        "provider": provider.name,
        "ocr": ocr.name,
        "semantic_provider_calls": semantic.calls,
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "p95_ms": sorted(times)[max(0, int(len(times) * .95) - 1)],
    })
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["text", "image"], default="text")
    ap.add_argument("--configured-provider", action="store_true", help="Use VEIL_SEMANTIC_PROVIDER instead of deterministic heuristic fallback")
    ap.add_argument("--limit", type=int, default=60, help="Image benchmark sample limit")
    args = ap.parse_args()
    result = run_text(args.configured_provider) if args.mode == "text" else run_image(args.configured_provider, args.limit)
    result["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    outdir = ROOT / "benchmarks" / "results"
    outdir.mkdir(parents=True, exist_ok=True)
    name = f"{args.mode}-{int(time.time())}.json"
    (outdir / name).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Saved {outdir / name}")


if __name__ == "__main__":
    main()
