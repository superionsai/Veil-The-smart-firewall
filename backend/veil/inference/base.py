from __future__ import annotations

from abc import ABC, abstractmethod


class SemanticProvider(ABC):
    name = "base"

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 220) -> str:
        raise NotImplementedError

    def status(self) -> dict:
        return {"name": self.name, "available": self.available()}
