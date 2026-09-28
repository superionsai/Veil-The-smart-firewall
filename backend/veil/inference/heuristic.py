from __future__ import annotations

import json
import re

from .base import SemanticProvider


class HeuristicProvider(SemanticProvider):
    name = "heuristic"

    def available(self) -> bool:
        return True

    def complete(self, system: str, user: str, max_tokens: int = 220) -> str:
        # This provider intentionally implements only the structured tasks Veil needs.
        if "VEIL_POLICY_COMPILER" in system:
            return self._compile_policy(user)
        return self._classify(user)

    def _classify(self, user: str) -> str:
        try:
            payload = json.loads(user)
            texts = payload.get("texts", [])
            custom_terms = [str(x).lower() for x in payload.get("custom_terms", [])]
        except Exception:
            texts = [user]
            custom_terms = []

        credential_hints = {"password", "passwd", "api_key", "api key", "openai_key", "github_token", "access_token", "auth_token", "database_url", "postgres://", "bearer "}
        confidential = {
            "confidential", "do not share", "don't share", "internal only", "nda",
            "acquisition", "merger", "salary", "compensation", "offer approved",
            "layoff", "termination", "client secret", "roadmap", "embargo",
            "unreleased", "private", "board meeting", "revenue forecast", "candidate offer", " lpa ", "ctc",
        }
        health = {"diagnosis", "prescription", "medical report", "patient", "blood test", "hospital"}
        location = {"home address", "current location", "live location", "residential address"}
        private_comm = {"don't tell", "do not tell", "between us", "personal message", "dm me"}

        results = []
        for text in texts:
            lower = str(text).lower()
            category = "PUBLIC"
            sensitive = False
            confidence = 0.18
            reason = "No strong semantic privacy signal"
            if any(k in lower for k in credential_hints):
                category, sensitive, confidence, reason = "AUTH_CREDENTIAL", True, 0.92, "Credential-like assignment or token context"
            elif any(term in lower for term in custom_terms if term):
                category, sensitive, confidence, reason = "CUSTOM", True, 0.96, "Matches a custom protected concept"
            elif any(k in lower for k in health):
                category, sensitive, confidence, reason = "HEALTH", True, 0.86, "Health-related private information"
            elif any(k in lower for k in location):
                category, sensitive, confidence, reason = "LOCATION", True, 0.86, "Private location information"
            elif any(k in lower for k in private_comm):
                category, sensitive, confidence, reason = "PRIVATE_COMMUNICATION", True, 0.86, "Language indicates a private communication"
            elif any(k in lower for k in confidential):
                category, sensitive, confidence, reason = "CONFIDENTIAL_WORK", True, 0.88, "Workplace confidentiality signal"
            results.append({"category": category, "sensitive": sensitive, "confidence": confidence, "reason": reason})
        return json.dumps({"results": results})

    def _compile_policy(self, user: str) -> str:
        lower = user.lower()
        hide = []
        keyword_map = {
            "credential": "AUTH_CREDENTIAL", "password": "AUTH_CREDENTIAL", "api key": "AUTH_CREDENTIAL",
            "salary": "CONFIDENTIAL_WORK", "compensation": "CONFIDENTIAL_WORK", "phone": "CONTACT",
            "email": "CONTACT", "financial": "FINANCIAL", "bank": "FINANCIAL", "health": "HEALTH",
            "medical": "HEALTH", "address": "LOCATION", "face": "FACE", "qr": "QR_CODE",
        }
        for keyword, category in keyword_map.items():
            if keyword in lower and category not in hide:
                hide.append(category)

        custom = []
        # Capture phrases such as "anything about Project Falcon" or "mentions of Project Orion".
        for pattern in [r"anything about ([^.\n,]+)", r"mention(?:ing|s of)? ([^.\n,]+)", r"hide ([A-Z][A-Za-z0-9 _-]{2,40})"]:
            for m in re.finditer(pattern, user, flags=re.I):
                term = m.group(1).strip(" .,'\"")
                if 2 < len(term) < 60 and not any(k in term.lower() for k in keyword_map):
                    custom.append({"concept": term, "action": "BLOCK"})

        allow_terms = []
        for pattern in [r"(?:allow|don't hide|do not hide|can remain visible)\s+([^.\n,]+)"]:
            for m in re.finditer(pattern, user, flags=re.I):
                allow_terms.append(m.group(1).strip(" .,'\""))

        return json.dumps({
            "hide_categories": hide,
            "custom_rules": custom,
            "allow_terms": allow_terms,
            "mask_faces": "face" in lower,
            "mask_qr": "qr" in lower or "code" in lower,
        })
