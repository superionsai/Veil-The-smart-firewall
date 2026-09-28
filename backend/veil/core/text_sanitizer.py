from __future__ import annotations

import re

from ..detection.regex_detector import TextRegexDetector
from ..inference.semantic import SemanticService
from ..models import Policy, PrivacyAction, PrivacyCategory
from ..policy import PolicyEngine


class TextSanitizer:
    def __init__(self, semantic: SemanticService):
        self.detector = TextRegexDetector()
        self.semantic = semantic
        self.policy_engine = PolicyEngine()

    def sanitize(self, text: str, policy: Policy) -> tuple[str, list[dict]]:
        detections = self.detector.detect(text)
        custom_terms = self.policy_engine.custom_terms(policy)

        # Add explicit custom terms with exact character spans.
        lower = text.lower()
        for term in custom_terms:
            start = 0
            while term and (idx := lower.find(term.lower(), start)) >= 0:
                detections.append({
                    "start": idx,
                    "end": idx + len(term),
                    "value": text[idx : idx + len(term)],
                    "category": PrivacyCategory.CUSTOM,
                    "confidence": 0.99,
                    "source": "policy:custom_term",
                    "reason": f"Matches protected concept: {term}",
                })
                start = idx + len(term)

        # Semantic classification is sentence/line-level. This may redact the whole line by design.
        lines = []
        offset = 0
        for part in re.split(r"(?<=\n)|(?<=[.!?])\s+", text):
            if part.strip():
                start = text.find(part, offset)
                lines.append((start, start + len(part), part.strip()))
                offset = start + len(part)
        candidates = [line[2] for line in lines if len(line[2]) >= 8]
        if policy.semantic_enabled and candidates:
            decisions = self.semantic.classify_many(candidates, policy.name, custom_terms)
            cursor = 0
            for start, end, line in lines:
                if len(line) < 8:
                    continue
                decision = decisions[cursor]
                cursor += 1
                if decision.sensitive and decision.category != PrivacyCategory.PUBLIC:
                    detections.append({
                        "start": start, "end": end, "value": text[start:end],
                        "category": decision.category, "confidence": decision.confidence,
                        "source": f"semantic:{self.semantic.provider.name}", "reason": decision.reason,
                    })

        detections = self._resolve(detections)
        actionable = []
        for d in detections:
            value_lower = str(d["value"]).lower()
            if any(term.lower() in value_lower for term in policy.allow_terms if term):
                continue
            action = policy.actions.get(d["category"].value, policy.default_action)
            if d["category"] == PrivacyCategory.CUSTOM:
                action = PrivacyAction.BLOCK
            if action == PrivacyAction.ALLOW:
                continue
            d["action"] = action
            actionable.append(d)

        sanitized = text
        for d in sorted(actionable, key=lambda x: x["start"], reverse=True):
            if d["action"] == PrivacyAction.WARN:
                continue
            label = f"[{d['category'].value.replace('_', ' ')}]"
            sanitized = sanitized[: d["start"]] + label + sanitized[d["end"] :]

        public = [
            {k: (v.value if hasattr(v, "value") else v) for k, v in d.items() if k != "value"}
            for d in actionable
        ]
        return sanitized, public

    @staticmethod
    def _resolve(items: list[dict]) -> list[dict]:
        chosen = []
        for item in sorted(items, key=lambda d: (d["start"], -(d["end"] - d["start"]), -float(d["confidence"]))):
            if any(not (item["end"] <= c["start"] or item["start"] >= c["end"]) for c in chosen):
                continue
            chosen.append(item)
        return sorted(chosen, key=lambda d: d["start"])
