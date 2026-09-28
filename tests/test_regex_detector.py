from veil.detection.regex_detector import RegexDetector, TextRegexDetector
from veil.models import Box, OCRBlock, PrivacyCategory


def block(text):
    return OCRBlock(text=text, box=Box(x=0, y=0, w=500, h=30), confidence=1)


def categories(text):
    return {r.category for r in RegexDetector().detect_block(block(text))}


def test_github_token():
    assert PrivacyCategory.AUTH_CREDENTIAL in categories("token=ghp_FAKEDEMO1234567890123456789012")


def test_email_is_contact_not_upi():
    cats = categories("person42@example.com")
    assert PrivacyCategory.CONTACT in cats
    assert PrivacyCategory.FINANCIAL not in cats


def test_upi_known_handle():
    assert PrivacyCategory.FINANCIAL in categories("pay demo-user@paytm")


def test_pan():
    assert PrivacyCategory.IDENTITY in categories("PAN ABCDE1234F")


def test_text_detector_returns_spans():
    text = "safe before person42@example.com safe after"
    items = TextRegexDetector().detect(text)
    assert items
    assert text[items[0]["start"]:items[0]["end"]] == "person42@example.com"
