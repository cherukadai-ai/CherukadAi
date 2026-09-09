"""Unit tests for password hashing: Argon2id, one-way, never plaintext."""
from app.core.security import hash_password, verify_password

PASSWORD = "Sup3rSecurePassw0rd!"


def test_hash_password_produces_argon2id_hash():
    result = hash_password(PASSWORD)
    assert result.startswith("$argon2")
    assert PASSWORD not in result


def test_hash_password_is_salted_per_call():
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_verify_password_roundtrip():
    assert verify_password(PASSWORD, hash_password(PASSWORD)) is True


def test_verify_password_rejects_wrong_password():
    assert verify_password("Wr0ngPassw0rd1", hash_password(PASSWORD)) is False
