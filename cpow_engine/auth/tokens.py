"""HMAC session tokens — no external JWT dependency."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time


class SessionTokenError(ValueError):
    pass


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def default_secret() -> str:
    return os.environ.get("CPOW_JWT_SECRET", "cpow-dev-secret-change-in-production")


def issue_session_token(
    user_id: str,
    *,
    secret: str | None = None,
    ttl_sec: float = 86_400.0,
) -> str:
    if not user_id:
        raise SessionTokenError("user_id_required")
    now = time.time()
    payload = {
        "sub": user_id,
        "iat": int(now),
        "exp": int(now + ttl_sec),
    }
    body = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    )
    key = (secret or default_secret()).encode()
    sig = hmac.new(key, body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64url_encode(sig)}"


def verify_session_token(
    token: str,
    *,
    secret: str | None = None,
    now: float | None = None,
) -> str:
    if not token or "." not in token:
        raise SessionTokenError("malformed_token")
    body, sig_part = token.rsplit(".", 1)
    key = (secret or default_secret()).encode()
    expected = hmac.new(key, body.encode(), hashlib.sha256).digest()
    try:
        provided = _b64url_decode(sig_part)
    except Exception as exc:
        raise SessionTokenError("invalid_signature") from exc
    if not hmac.compare_digest(expected, provided):
        raise SessionTokenError("invalid_signature")

    try:
        payload = json.loads(_b64url_decode(body))
    except Exception as exc:
        raise SessionTokenError("invalid_payload") from exc

    ts = now if now is not None else time.time()
    exp = float(payload.get("exp", 0))
    if exp < ts:
        raise SessionTokenError("token_expired")
    sub = str(payload.get("sub", ""))
    if not sub:
        raise SessionTokenError("missing_subject")
    return sub
