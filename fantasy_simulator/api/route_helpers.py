"""Authenticated area/governance route helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from api.auth_deps import bind_session_actor


def _normalize_body(body: Any, *, exclude_none: bool) -> dict[str, Any]:
    if hasattr(body, "model_dump"):
        return body.model_dump(exclude_none=exclude_none)
    if isinstance(body, dict):
        return dict(body)
    return body


def authed_payload(
    body: Any,
    auth_user: str | None,
    *actor_fields: str,
    exclude_none: bool = False,
) -> dict[str, Any]:
    return bind_session_actor(
        _normalize_body(body, exclude_none=exclude_none),
        auth_user,
        *actor_fields,
    )


def authed_call(
    handler: Callable[[dict[str, Any]], dict[str, Any]],
    body: Any,
    auth_user: str | None,
    *actor_fields: str,
    exclude_none: bool = False,
) -> dict[str, Any]:
    return handler(
        authed_payload(body, auth_user, *actor_fields, exclude_none=exclude_none),
    )


def authed_call_404(
    handler: Callable[[dict[str, Any]], dict[str, Any]],
    body: Any,
    auth_user: str | None,
    *actor_fields: str,
    exclude_none: bool = False,
) -> dict[str, Any]:
    try:
        return authed_call(
            handler, body, auth_user, *actor_fields, exclude_none=exclude_none,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def authed_call_400(
    handler: Callable[[dict[str, Any]], dict[str, Any]],
    body: Any,
    auth_user: str | None,
    *actor_fields: str,
    exclude_none: bool = False,
) -> dict[str, Any]:
    try:
        return authed_call(
            handler, body, auth_user, *actor_fields, exclude_none=exclude_none,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
