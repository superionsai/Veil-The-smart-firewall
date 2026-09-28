from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .core import FileSanitizer, FrameProcessor, TextSanitizer
from .inference import SemanticService, make_semantic_provider
from .metrics import AuditStore, RuntimeMetrics
from .models import CompilePolicyRequest, Policy, TextSanitizeRequest, TextSanitizeResponse
from .ocr import make_ocr_provider
from .policy import PRESETS, PolicyCompiler, get_policy


@asynccontextmanager
async def lifespan(_app):
    yield
    provider = globals().get("semantic_provider")
    close = getattr(provider, "close", None)
    if callable(close):
        close()


app = FastAPI(
    title="Veil",
    description="On-device semantic privacy firewall for live screen and file sharing.",
    version="1.0.0",
    lifespan=lifespan,
)

ocr_provider = make_ocr_provider(settings.ocr_provider)
semantic_provider = make_semantic_provider(settings)
semantic_service = SemanticService(semantic_provider)
audit_store = AuditStore(settings.db_path, settings.audit_enabled, settings.retain_raw_text)
runtime_metrics = RuntimeMetrics()
policy_compiler = PolicyCompiler(semantic_provider)
text_sanitizer = TextSanitizer(semantic_service)


def make_processor(session_prefix: str = "live") -> FrameProcessor:
    return FrameProcessor(
        settings=settings,
        ocr=ocr_provider,
        semantic=semantic_service,
        audit=audit_store,
        runtime_metrics=runtime_metrics,
        session_id=f"{session_prefix}-{uuid.uuid4().hex[:10]}",
    )


file_sanitizer = FileSanitizer(settings.output_dir, make_processor)

settings.output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=settings.output_dir), name="outputs")
app.mount("/static", StaticFiles(directory=settings.frontend_dir), name="static")


@app.get("/")
def index():
    return FileResponse(settings.frontend_dir / "index.html")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "app": settings.app_name,
        "platform": settings.platform_summary,
        "snapdragon_windows": settings.likely_snapdragon_windows,
        "ocr": {"name": ocr_provider.name, "available": ocr_provider.available()},
        "semantic": semantic_service.status(),
        "audit_enabled": settings.audit_enabled,
        "retain_raw_text": settings.retain_raw_text,
    }


@app.get("/api/config")
def config():
    return {
        "presets": [p.model_dump(mode="json") for p in PRESETS.values()],
        "live_process_interval_ms": settings.live_process_interval_ms,
        "retain_raw_text": settings.retain_raw_text,
    }


@app.post("/api/policy/compile")
async def compile_policy(req: CompilePolicyRequest):
    if not req.text.strip():
        raise HTTPException(400, "Policy text is empty")
    try:
        policy = await asyncio.to_thread(policy_compiler.compile, req.text, req.base_policy)
        return policy.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(500, f"Could not compile policy: {exc}") from exc


@app.post("/api/sanitize/text", response_model=TextSanitizeResponse)
async def sanitize_text(req: TextSanitizeRequest):
    policy = req.custom_policy or get_policy(req.policy)
    sanitized, detections = await asyncio.to_thread(text_sanitizer.sanitize, req.text, policy)
    return TextSanitizeResponse(sanitized_text=sanitized, detections=detections)


@app.post("/api/sanitize/file")
async def sanitize_file(
    file: UploadFile = File(...),
    policy: str = Form("external"),
    policy_json: str | None = Form(None),
):
    content = await file.read()
    if len(content) > 80 * 1024 * 1024:
        raise HTTPException(413, "File too large. Maximum demo upload size is 80 MB.")
    selected = get_policy(policy)
    if policy_json:
        try:
            selected = Policy.model_validate_json(policy_json)
        except Exception as exc:
            raise HTTPException(400, f"Invalid policy_json: {exc}") from exc
    try:
        return await asyncio.to_thread(file_sanitizer.sanitize, file.filename or "upload", content, selected)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Sanitization failed: {exc}") from exc


@app.get("/api/metrics")
def metrics():
    return {
        "runtime": runtime_metrics.snapshot(),
        "audit": audit_store.aggregate(),
        "semantic": semantic_service.status(),
        "ocr": {"name": ocr_provider.name, "available": ocr_provider.available()},
    }


@app.get("/api/audit/recent")
def recent_audit(limit: int = 50):
    return {"events": audit_store.recent(limit)}


@app.delete("/api/audit")
def clear_audit():
    audit_store.clear()
    return {"ok": True}


@app.websocket("/ws/live")
async def live_socket(ws: WebSocket):
    await ws.accept()
    processor = make_processor("live")
    policy = get_policy(ws.query_params.get("policy", "external"))
    try:
        await ws.send_json({"type": "ready", "session_id": processor.session_id, "policy": policy.id})
        while True:
            message = await ws.receive()
            if message.get("type") == "websocket.disconnect":
                break
            if message.get("text") is not None:
                try:
                    command = json.loads(message["text"])
                    if command.get("type") == "policy":
                        if isinstance(command.get("policy"), dict):
                            policy = Policy.model_validate(command["policy"])
                        else:
                            policy = get_policy(str(command.get("policy_id", "external")))
                        await ws.send_json({"type": "policy_ack", "policy": policy.id})
                    elif command.get("type") == "ping":
                        await ws.send_json({"type": "pong"})
                except Exception as exc:
                    await ws.send_json({"type": "error", "message": f"Invalid command: {exc}"})
                continue
            data = message.get("bytes")
            if not data:
                continue
            try:
                result = await asyncio.to_thread(processor.process_bytes, data, policy, False)
                await ws.send_json({"type": "frame", **result.model_dump(mode="json")})
            except Exception as exc:
                await ws.send_json({"type": "error", "message": str(exc)})
    except WebSocketDisconnect:
        pass

