"""FastAPI auth dependencies — Bearer session tokens."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import Header, HTTPException

from cpow_engine.auth import SessionTokenError, verify_session_token


def auth_required() -> bool:
    return os.environ.get("CPOW_AUTH_REQUIRED", "0").lower() in ("1", "true", "yes")


def _parse_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    try:
        return verify_session_token(parts[1])
    except SessionTokenError:
        return None


def optional_user(authorization: str | None = Header(None)) -> str | None:
    return _parse_bearer(authorization)


def require_user(authorization: str | None = Header(None)) -> str:
    user_id = _parse_bearer(authorization)
    if user_id:
        return user_id
    if auth_required():
        raise HTTPException(status_code=401, detail="auth_required")
    return ""


def require_authenticated_user(authorization: str | None = Header(None)) -> str:
    user_id = _parse_bearer(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="auth_required")
    return user_id


def bind_session_actor(
    payload: dict,
    auth_user: str | None,
    *fields: str,
) -> dict:
    """Bearer 세션이 있으면 actor 필드를 세션 사용자로 고정."""
    out = dict(payload)
    if not auth_user:
        return out
    for field in fields:
        if field in out and str(out[field]) not in ("anonymous", auth_user, ""):
            raise HTTPException(status_code=403, detail="actor_identity_mismatch")
        out[field] = auth_user
    return out
