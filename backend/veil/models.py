from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PrivacyCategory(str, Enum):
    AUTH_CREDENTIAL = "AUTH_CREDENTIAL"
    IDENTITY = "IDENTITY"
    CONTACT = "CONTACT"
    FINANCIAL = "FINANCIAL"
    CONFIDENTIAL_WORK = "CONFIDENTIAL_WORK"
    PRIVATE_COMMUNICATION = "PRIVATE_COMMUNICATION"
    HEALTH = "HEALTH"
    LOCATION = "LOCATION"
    QR_CODE = "QR_CODE"
    FACE = "FACE"
    CUSTOM = "CUSTOM"
    PUBLIC = "PUBLIC"
    UNKNOWN = "UNKNOWN"


class PrivacyAction(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    BLUR = "BLUR"
    REPLACE = "REPLACE"
    WARN = "WARN"


class Box(BaseModel):
    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    def clamp(self, width: int, height: int) -> "Box":
        x = max(0, min(self.x, width))
        y = max(0, min(self.y, height))
        x2 = max(x, min(self.x2, width))
        y2 = max(y, min(self.y2, height))
        return Box(x=x, y=y, w=max(0, x2 - x), h=max(0, y2 - y))

    def normalized(self, width: int, height: int) -> dict[str, float]:
        if width <= 0 or height <= 0:
            return {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}
        return {
            "x": self.x / width,
            "y": self.y / height,
            "w": self.w / width,
            "h": self.h / height,
        }


class OCRBlock(BaseModel):
    text: str
    box: Box
    confidence: float = 1.0


class PrivacyRegion(BaseModel):
    box: Box
    category: PrivacyCategory
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    action: PrivacyAction = PrivacyAction.BLOCK
    text: str | None = None
    replacement: str | None = None
    reason: str | None = None
    detector_meta: dict[str, Any] = Field(default_factory=dict)

    def public_dict(self, width: int, height: int, include_text: bool = False) -> dict[str, Any]:
        payload = {
            "box": self.box.normalized(width, height),
            "pixel_box": self.box.model_dump(),
            "category": self.category.value,
            "confidence": round(float(self.confidence), 4),
            "source": self.source,
            "action": self.action.value,
            "replacement": self.replacement,
            "reason": self.reason,
        }
        if include_text:
            payload["text"] = self.text
        return payload


class SemanticDecision(BaseModel):
    category: PrivacyCategory = PrivacyCategory.UNKNOWN
    sensitive: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str | None = None


class CustomRule(BaseModel):
    concept: str
    action: PrivacyAction = PrivacyAction.BLOCK


class Policy(BaseModel):
    id: str
    name: str
    description: str = ""
    actions: dict[str, PrivacyAction] = Field(default_factory=dict)
    custom_rules: list[CustomRule] = Field(default_factory=list)
    allow_terms: list[str] = Field(default_factory=list)
    default_action: PrivacyAction = PrivacyAction.ALLOW
    semantic_enabled: bool = True
    mask_faces: bool = False
    mask_qr: bool = True


class FrameMetrics(BaseModel):
    total_ms: float = 0.0
    change_ms: float = 0.0
    ocr_ms: float = 0.0
    detection_ms: float = 0.0
    semantic_ms: float = 0.0
    visual_ms: float = 0.0
    changed_fraction: float = 1.0
    ocr_blocks: int = 0
    semantic_candidates: int = 0
    semantic_calls: int = 0
    regions: int = 0
    skipped: bool = False


class FrameResult(BaseModel):
    width: int
    height: int
    regions: list[dict[str, Any]]
    metrics: FrameMetrics


class CompilePolicyRequest(BaseModel):
    text: str
    base_policy: str = "external"


class TextSanitizeRequest(BaseModel):
    text: str
    policy: str = "external"
    custom_policy: Policy | None = None


class TextSanitizeResponse(BaseModel):
    sanitized_text: str
    detections: list[dict[str, Any]]
