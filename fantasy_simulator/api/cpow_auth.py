"""CPoW account auth — register / login / session tokens."""

from __future__ import annotations

from typing import Any

from cpow_engine.auth import AccountRegistry, AccountResult, issue_session_token

_accounts = AccountRegistry()


def _auth_token_response(result: AccountResult) -> dict[str, Any]:
    token = issue_session_token(result.user_id)
    return {
        "ok": True,
        "reason": result.reason,
        "user_id": result.user_id,
        "token": token,
        "token_type": "Bearer",
    }


def handle_auth_register(payload: dict[str, Any]) -> dict[str, Any]:
    user_id = str(payload.get("user_id", "")).strip()
    password = str(payload.get("password", ""))
    result = _accounts.register(user_id, password)
    if not result.ok:
        return {"ok": False, "reason": result.reason}
    return _auth_token_response(result)


def handle_auth_login(payload: dict[str, Any]) -> dict[str, Any]:
    user_id = str(payload.get("user_id", "")).strip()
    password = str(payload.get("password", ""))
    result = _accounts.authenticate(user_id, password)
    if not result.ok:
        return {"ok": False, "reason": result.reason}
    return _auth_token_response(result)


def handle_auth_me(auth_user_id: str) -> dict[str, Any]:
    return {
        "ok": True,
        "user_id": auth_user_id,
        "registered": _accounts.exists(auth_user_id),
    }
