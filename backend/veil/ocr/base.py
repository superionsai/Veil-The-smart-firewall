from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from ..models import OCRBlock


class OCRProvider(ABC):
    name = "base"

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def extract(self, image: Image.Image) -> list[OCRBlock]:
        raise NotImplementedError
