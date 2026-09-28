import os
os.environ.setdefault("VEIL_SEMANTIC_PROVIDER", "heuristic")
os.environ.setdefault("VEIL_OCR_PROVIDER", "none")

from fastapi.testclient import TestClient
from veil.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_text_endpoint():
    r = client.post("/api/sanitize/text", json={
        "text": "OPENAI_KEY=sk-THIS_IS_A_FAKE_DEMO_TOKEN_123456789",
        "policy": "external",
    })
    assert r.status_code == 200
    assert "AUTH CREDENTIAL" in r.json()["sanitized_text"]
