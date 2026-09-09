"""Argon2id password hasher implementing the domain PasswordHasher port."""
from __future__ import annotations

from app.core.security import hash_password, verify_password
from app.modules.identity.domain.ports import PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    def hash(self, plain_password: str) -> str:
        return hash_password(plain_password)

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return verify_password(plain_password, password_hash)
