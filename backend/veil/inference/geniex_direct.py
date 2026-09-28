from __future__ import annotations

import threading

from .base import SemanticProvider


class GenieXDirectProvider(SemanticProvider):
    name = "geniex_direct"

    def __init__(self, model: str, device_map: str = "qairt"):
        self.model_id = model
        self.device_map = device_map
        self._model = None
        self._lock = threading.RLock()

    def available(self) -> bool:
        try:
            import geniex  # noqa: F401
            return True
        except Exception:
            return False

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                from geniex import AutoModelForCausalLM

                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    device_map=self.device_map,
                )
        return self._model

    def complete(self, system: str, user: str, max_tokens: int = 220) -> str:
        model = self._ensure_model()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        prompt = model.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        with self._lock:
            output = model.generate(prompt, max_new_tokens=max_tokens, temperature=0.0)
        return output.text

    def status(self) -> dict:
        return {
            "name": self.name,
            "available": self.available(),
            "model": self.model_id,
            "device_map": self.device_map,
            "loaded": self._model is not None,
        }

    def close(self):
        with self._lock:
            if self._model is not None:
                try:
                    self._model.close()
                finally:
                    self._model = None
