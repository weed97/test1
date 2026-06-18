"""Account registry — password hashing with stdlib PBKDF2."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        120_000,
    )


@dataclass
class AccountRecord:
    user_id: str
    salt: bytes
    password_hash: bytes
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def verify(self, password: str) -> bool:
        import hmac

        trial = _hash_password(password, self.salt)
        return hmac.compare_digest(trial, self.password_hash)


@dataclass
class AccountResult:
    ok: bool
    reason: str = ""
    user_id: str = ""


class AccountRegistry:
    def __init__(self) -> None:
        self._accounts: dict[str, AccountRecord] = {}

    def register(self, user_id: str, password: str) -> AccountResult:
        uid = user_id.strip()
        if len(uid) < 3:
            return AccountResult(False, reason="user_id_too_short")
        if len(password) < 8:
            return AccountResult(False, reason="password_too_short")
        if uid in self._accounts:
            return AccountResult(False, reason="user_id_taken")
        salt = secrets.token_bytes(16)
        self._accounts[uid] = AccountRecord(
            user_id=uid,
            salt=salt,
            password_hash=_hash_password(password, salt),
        )
        return AccountResult(True, reason="registered", user_id=uid)

    def authenticate(self, user_id: str, password: str) -> AccountResult:
        rec = self._accounts.get(user_id.strip())
        if rec is None:
            return AccountResult(False, reason="invalid_credentials")
        if not rec.verify(password):
            return AccountResult(False, reason="invalid_credentials")
        return AccountResult(True, reason="authenticated", user_id=rec.user_id)

    def exists(self, user_id: str) -> bool:
        return user_id in self._accounts
