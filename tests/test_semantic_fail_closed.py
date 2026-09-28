from veil.inference.semantic import SemanticService
from veil.models import PrivacyCategory


class BrokenProvider:
    name = "broken"
    def available(self): return True
    def status(self): return {"name": self.name, "available": True}
    def complete(self, *args, **kwargs): return "not-json"


def test_semantic_failure_is_fail_closed():
    service = SemanticService(BrokenProvider())
    result = service.classify_many(["possibly sensitive text"], "External Meeting")
    assert result[0].sensitive is True
    assert result[0].category == PrivacyCategory.UNKNOWN
