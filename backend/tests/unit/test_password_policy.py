"""Unit tests for the credential password policy (no infrastructure)."""
import pytest

from app.core.exceptions import ValidationAppError
from app.modules.identity.domain.services import PasswordPolicy

policy = PasswordPolicy(min_length=12)


def test_accepts_strong_password():
    policy.validate("Sup3rSecurePassw0rd!", email="admin@example.com")


def test_rejects_too_short_password():
    with pytest.raises(ValidationAppError):
        policy.validate("Sh0rt", email="admin@example.com")


def test_rejects_password_without_digit():
    with pytest.raises(ValidationAppError):
        policy.validate("OnlyLettersHere!", email="admin@example.com")


def test_rejects_password_without_letter():
    with pytest.raises(ValidationAppError):
        policy.validate("12345678901234", email="admin@example.com")


def test_rejects_password_containing_email():
    with pytest.raises(ValidationAppError):
        policy.validate("admin@example.com1", email="admin@example.com")


def test_custom_min_length_is_enforced():
    strict = PasswordPolicy(min_length=16)
    with pytest.raises(ValidationAppError):
        strict.validate("Sh0rtButOk12", email="admin@example.com")
