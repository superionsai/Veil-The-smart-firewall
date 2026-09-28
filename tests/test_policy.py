from veil.inference.heuristic import HeuristicProvider
from veil.models import Box, PrivacyAction, PrivacyCategory, PrivacyRegion
from veil.policy import PolicyCompiler, PolicyEngine, get_policy


def test_external_blocks_credentials():
    p = get_policy("external")
    r = PrivacyRegion(box=Box(x=0,y=0,w=10,h=10), category=PrivacyCategory.AUTH_CREDENTIAL, confidence=1, source="test")
    out = PolicyEngine().apply(r, p)
    assert out.action == PrivacyAction.BLOCK


def test_allow_term_overrides():
    p = get_policy("external")
    p.allow_terms = ["demo.user@example.com"]
    r = PrivacyRegion(box=Box(x=0,y=0,w=10,h=10), text="demo.user@example.com", category=PrivacyCategory.CONTACT, confidence=1, source="test")
    out = PolicyEngine().apply(r, p)
    assert out.action == PrivacyAction.ALLOW


def test_heuristic_policy_compile_custom_term():
    p = PolicyCompiler(HeuristicProvider()).compile(
        "Hide credentials and anything about Project Orion. QR codes should also be hidden.",
        "external",
    )
    assert p.actions["AUTH_CREDENTIAL"] == PrivacyAction.BLOCK
    assert any(r.concept.lower() == "project orion" for r in p.custom_rules)
    assert p.mask_qr is True

class _FailingProvider:
    name = "failing"
    def available(self): return False
    def complete(self, *args, **kwargs): raise RuntimeError("model unavailable")


def test_policy_compiler_falls_back_locally_when_model_is_unavailable():
    p = PolicyCompiler(_FailingProvider()).compile("Hide credentials and anything about Project Falcon.", "external")
    assert p.actions["AUTH_CREDENTIAL"] == PrivacyAction.BLOCK
    assert any(r.concept.lower() == "project falcon" for r in p.custom_rules)
