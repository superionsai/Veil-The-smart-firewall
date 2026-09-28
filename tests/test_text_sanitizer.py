from veil.core.text_sanitizer import TextSanitizer
from veil.inference.heuristic import HeuristicProvider
from veil.inference.semantic import SemanticService
from veil.policy import get_policy


def test_secret_redaction():
    s = TextSanitizer(SemanticService(HeuristicProvider()))
    text = "key sk-THIS_IS_A_FAKE_DEMO_TOKEN_123456789 end"
    safe, detections = s.sanitize(text, get_policy("external"))
    assert "sk-THIS" not in safe
    assert detections


def test_semantic_confidential_redaction():
    s = TextSanitizer(SemanticService(HeuristicProvider()))
    text = "Project Orion acquisition estimate is confidential."
    safe, detections = s.sanitize(text, get_policy("external"))
    assert safe != text
    assert any(d["category"] == "CONFIDENTIAL_WORK" for d in detections)


def test_safe_sentence_remains():
    s = TextSanitizer(SemanticService(HeuristicProvider()))
    text = "Meeting moved to Friday."
    safe, detections = s.sanitize(text, get_policy("external"))
    assert safe == text
    assert detections == []
