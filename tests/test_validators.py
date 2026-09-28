from veil.detection.validators import luhn_valid, verhoeff_valid


def test_luhn_valid_known_test_card():
    assert luhn_valid("4242 4242 4242 4242")
    assert not luhn_valid("4242 4242 4242 4243")


def test_verhoeff_rejects_random_12_digits():
    assert not verhoeff_valid("1111 2222 3334")
