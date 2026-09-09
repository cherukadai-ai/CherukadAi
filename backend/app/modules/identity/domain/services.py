"""Domain services: password policy enforcement for credential-setting flows."""
from __future__ import annotations

import re

from app.core.exceptions import ValidationAppError

_LETTER_RE = re.compile(r"[A-Za-z]")
_DIGIT_RE = re.compile(r"\d")


class PasswordPolicy:
    """Validates candidate passwords for new credentials.

    Policy: minimum length (default 12), at least one letter and one digit, and
    must not contain the account's email address (case-insensitive).
    """

    def __init__(self, min_length: int = 12) -> None:
        self._min_length = min_length

    def validate(self, password: str, *, email: str) -> None:
        if len(password) < self._min_length:
            raise ValidationAppError(
                f"Password must be at least {self._min_length} characters long."
            )
        if not _LETTER_RE.search(password) or not _DIGIT_RE.search(password):
            raise ValidationAppError("Password must contain at least one letter and one digit.")
        local_part = email.split("@", 1)[0].strip().lower()
        if local_part and local_part in password.lower():
            raise ValidationAppError("Password must not contain the account email.")
