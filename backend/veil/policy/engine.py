from __future__ import annotations

from ..models import Policy, PrivacyAction, PrivacyRegion
from ..utils import compact_space


class PolicyEngine:
    @staticmethod
    def custom_terms(policy: Policy) -> list[str]:
        return [r.concept for r in policy.custom_rules if r.concept.strip()]

    def apply(self, region: PrivacyRegion, policy: Policy) -> PrivacyRegion:
        text_lower = compact_space(region.text or "").lower()
        for allowed in policy.allow_terms:
            if allowed.strip() and allowed.lower() in text_lower:
                region.action = PrivacyAction.ALLOW
                region.reason = (region.reason or "") + " · allowed by explicit exception"
                return region

        # Custom terms override the generic class when text matches.
        for rule in policy.custom_rules:
            if text_lower and rule.concept.lower() in text_lower:
                region.action = rule.action
                region.reason = f"Matches protected concept: {rule.concept}"
                return region

        region.action = policy.actions.get(region.category.value, policy.default_action)
        return region

    def filter_actionable(self, regions: list[PrivacyRegion], policy: Policy) -> list[PrivacyRegion]:
        out = []
        for region in regions:
            region = self.apply(region, policy)
            if region.action != PrivacyAction.ALLOW:
                out.append(region)
        return out
