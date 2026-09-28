from __future__ import annotations

import httpx

from .base import SemanticProvider


class GenieXServerProvider(SemanticProvider):
    name = "geniex_server"

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def available(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/models", timeout=0.8)
            return r.status_code == 200
        except Exception:
            return False

    def complete(self, system: str, user: str, max_tokens: int = 220) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=90.0) as client:
            r = client.post(f"{self.base_url}/chat/completions", json=payload)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]

    def status(self) -> dict:
        return {"name": self.name, "available": self.available(), "base_url": self.base_url, "model": self.model}
