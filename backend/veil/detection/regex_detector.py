from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import Box, OCRBlock, PrivacyCategory, PrivacyRegion
from ..utils import compact_space
from .validators import luhn_valid, verhoeff_valid


@dataclass(frozen=True)
class PatternRule:
    name: str
    pattern: re.Pattern[str]
    category: PrivacyCategory
    confidence: float
    reason: str


FLAGS = re.IGNORECASE | re.MULTILINE
RULES: tuple[PatternRule, ...] = (
    PatternRule("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", FLAGS), PrivacyCategory.AUTH_CREDENTIAL, 1.0, "Private-key material"),
    PatternRule("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,255}\b"), PrivacyCategory.AUTH_CREDENTIAL, 1.0, "GitHub access token"),
    PatternRule("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), PrivacyCategory.AUTH_CREDENTIAL, 0.99, "API key pattern"),
    PatternRule("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), PrivacyCategory.AUTH_CREDENTIAL, 1.0, "AWS access-key identifier"),
    PatternRule("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), PrivacyCategory.AUTH_CREDENTIAL, 0.99, "JWT bearer token"),
    PatternRule("bearer", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}\b", FLAGS), PrivacyCategory.AUTH_CREDENTIAL, 0.98, "Bearer credential"),
    PatternRule("credential_assignment", re.compile(r"\b(?:password|passwd|pwd|secret|api[_-]?key|openai[_-]?key|github[_-]?token|access[_-]?token|auth[_-]?token|database[_-]?url|db[_-]?url)\s*[:=]\s*['\"]?[^\s'\"]{6,}", FLAGS), PrivacyCategory.AUTH_CREDENTIAL, 0.97, "Credential assignment"),
    PatternRule("database_url", re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s]+", FLAGS), PrivacyCategory.AUTH_CREDENTIAL, 0.98, "Database connection string"),
    PatternRule("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", FLAGS), PrivacyCategory.CONTACT, 0.98, "Email address"),
    PatternRule("pan", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), PrivacyCategory.IDENTITY, 0.98, "Indian PAN-like identifier"),
    PatternRule("ifsc", re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"), PrivacyCategory.FINANCIAL, 0.94, "Indian IFSC code"),
    PatternRule("upi", re.compile(r"\b[A-Z0-9._-]{2,}@(ybl|paytm|oksbi|okaxis|okhdfcbank|okicici|axl|ibl|apl|upi)\b", FLAGS), PrivacyCategory.FINANCIAL, 0.94, "UPI payment address"),
    PatternRule("india_phone", re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)"), PrivacyCategory.CONTACT, 0.90, "Indian mobile number"),
)

COMMON_FALSE_POSITIVE_HINTS = {
    "example@example.com",
    "test@test.com",
    "user@example.com",
}


class RegexDetector:
    name = "deterministic"

    def detect_block(self, block: OCRBlock) -> list[PrivacyRegion]:
        text = compact_space(block.text)
        if not text:
            return []
        lower = text.lower()
        found: list[PrivacyRegion] = []
        for rule in RULES:
            for match in rule.pattern.finditer(text):
                matched = match.group(0)
                confidence = rule.confidence
                if matched.lower() in COMMON_FALSE_POSITIVE_HINTS:
                    confidence = min(confidence, 0.45)
                found.append(
                    PrivacyRegion(
                        box=block.box,
                        text=matched,
                        category=rule.category,
                        confidence=confidence,
                        source=f"regex:{rule.name}",
                        reason=rule.reason,
                    )
                )

        # Aadhaar-like candidate: require proper grouping/length and reward Verhoeff validity.
        for match in re.finditer(r"(?<!\d)(?:\d{4}[ -]?){2}\d{4}(?!\d)", text):
            candidate = match.group(0)
            valid = verhoeff_valid(candidate)
            found.append(
                PrivacyRegion(
                    box=block.box,
                    text=candidate,
                    category=PrivacyCategory.IDENTITY,
                    confidence=0.99 if valid else 0.78,
                    source="validator:aadhaar_verhoeff" if valid else "pattern:aadhaar_like",
                    reason="Aadhaar-format identifier" if valid else "12-digit identity-number candidate",
                )
            )

        # Payment card: only flag as high-confidence when Luhn passes.
        for match in re.finditer(r"(?<!\d)(?:\d[ -]?){12,19}(?!\d)", text):
            candidate = match.group(0).strip()
            digits = re.sub(r"\D", "", candidate)
            if 13 <= len(digits) <= 19 and luhn_valid(candidate):
                found.append(
                    PrivacyRegion(
                        box=block.box,
                        text=candidate,
                        category=PrivacyCategory.FINANCIAL,
                        confidence=0.99,
                        source="validator:luhn",
                        reason="Luhn-valid payment-card number",
                    )
                )

        # De-duplicate a block if several detectors identify the same category.
        best: dict[PrivacyCategory, PrivacyRegion] = {}
        for region in found:
            if region.category not in best or region.confidence > best[region.category].confidence:
                best[region.category] = region
        return list(best.values())

    def detect(self, blocks: list[OCRBlock]) -> list[PrivacyRegion]:
        out: list[PrivacyRegion] = []
        for block in blocks:
            out.extend(self.detect_block(block))
        return out


class TextRegexDetector:
    """Character-span detector used by Quick Paste sanitization."""

    def detect(self, text: str) -> list[dict]:
        matches: list[dict] = []
        for rule in RULES:
            for m in rule.pattern.finditer(text):
                matches.append({
                    "start": m.start(),
                    "end": m.end(),
                    "value": m.group(0),
                    "category": rule.category,
                    "confidence": rule.confidence,
                    "source": f"regex:{rule.name}",
                    "reason": rule.reason,
                })
        for m in re.finditer(r"(?<!\d)(?:\d[ -]?){12,19}(?!\d)", text):
            if luhn_valid(m.group(0)):
                matches.append({
                    "start": m.start(), "end": m.end(), "value": m.group(0),
                    "category": PrivacyCategory.FINANCIAL, "confidence": 0.99,
                    "source": "validator:luhn", "reason": "Luhn-valid payment-card number",
                })
        for m in re.finditer(r"(?<!\d)(?:\d{4}[ -]?){2}\d{4}(?!\d)", text):
            matches.append({
                "start": m.start(), "end": m.end(), "value": m.group(0),
                "category": PrivacyCategory.IDENTITY,
                "confidence": 0.99 if verhoeff_valid(m.group(0)) else 0.78,
                "source": "validator:aadhaar_verhoeff" if verhoeff_valid(m.group(0)) else "pattern:aadhaar_like",
                "reason": "Aadhaar-format identifier",
            })
        return self._resolve_overlaps(matches)

    @staticmethod
    def _resolve_overlaps(matches: list[dict]) -> list[dict]:
        chosen: list[dict] = []
        for item in sorted(matches, key=lambda m: (m["start"], -(m["end"] - m["start"]), -m["confidence"])):
            if any(not (item["end"] <= c["start"] or item["start"] >= c["end"]) for c in chosen):
                continue
            chosen.append(item)
        return sorted(chosen, key=lambda m: m["start"])
