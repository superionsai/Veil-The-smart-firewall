from __future__ import annotations

import json
import re
import uuid

from ..inference.base import SemanticProvider
from ..inference.heuristic import HeuristicProvider
from ..models import CustomRule, Policy, PrivacyAction
from ..utils import extract_json_object
from .presets import get_policy


SYSTEM = """You are VEIL_POLICY_COMPILER.
Convert a natural-language privacy policy into JSON only.
Do not invent personal facts. Supported categories are AUTH_CREDENTIAL, IDENTITY, CONTACT, FINANCIAL,
CONFIDENTIAL_WORK, PRIVATE_COMMUNICATION, HEALTH, LOCATION, QR_CODE, FACE, CUSTOM.
Schema: {"hide_categories":["..."],"warn_categories":["..."],"custom_rules":[{"concept":"...","action":"BLOCK"}],"allow_terms":["..."],"mask_faces":true|false,"mask_qr":true|false}.
Only include categories/concepts clearly requested by the user."""


class PolicyCompiler:
    def __init__(self, provider: SemanticProvider):
        self.provider = provider

    def compile(self, text: str, base_policy: str = "external") -> Policy:
        base = get_policy(base_policy)
        try:
            raw = self.provider.complete(SYSTEM, text, max_tokens=320)
            data = extract_json_object(raw)
        except Exception:
            # Policy editing should remain usable even if the accelerator/model is
            # temporarily unavailable. The fallback is deterministic and local.
            raw = HeuristicProvider().complete(SYSTEM, text, max_tokens=320)
            data = extract_json_object(raw)

        hide = data.get("hide_categories", []) if isinstance(data, dict) else []
        warn = data.get("warn_categories", []) if isinstance(data, dict) else []
        for category in hide:
            if isinstance(category, str):
                base.actions[category] = PrivacyAction.BLOCK
        for category in warn:
            if isinstance(category, str):
                base.actions[category] = PrivacyAction.WARN

        rules = []
        for item in (data.get("custom_rules", []) if isinstance(data, dict) else []):
            if not isinstance(item, dict):
                continue
            concept = str(item.get("concept", "")).strip()
            if not concept:
                continue
            try:
                action = PrivacyAction(str(item.get("action", "BLOCK")))
            except Exception:
                action = PrivacyAction.BLOCK
            rules.append(CustomRule(concept=concept[:100], action=action))
        base.custom_rules = rules

        allow_terms = data.get("allow_terms", []) if isinstance(data, dict) else []
        base.allow_terms = [str(x).strip()[:100] for x in allow_terms if str(x).strip()]
        if isinstance(data, dict) and "mask_faces" in data:
            base.mask_faces = bool(data["mask_faces"])
        if isinstance(data, dict) and "mask_qr" in data:
            base.mask_qr = bool(data["mask_qr"])

        base.id = f"custom-{uuid.uuid4().hex[:8]}"
        base.name = "Custom Policy"
        base.description = text.strip()[:300]
        return base
