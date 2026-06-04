"""Test double for LLMClient — inject predictable responses in unit tests."""

from __future__ import annotations

from typing import Any, Callable

from utils.llm_errors import LLMCallError


class MockLLMClient:
    """Minimal LLMClient stand-in for hybrid / llm mode tests."""

    def __init__(
        self,
        *,
        narrator_text: str = "Mock narrator response.",
        on_call: Callable[[str, str, dict[str, Any]], dict[str, Any] | None] | None = None,
        fail_roles: set[str] | None = None,
    ) -> None:
        self.narrator_text = narrator_text
        self.on_call = on_call
        self.fail_roles = fail_roles or set()
        self.calls: list[dict[str, Any]] = []

    def _record(self, family: str, action: str, role: str, **kwargs: Any) -> None:
        self.calls.append({"family": family, "action": action, "role": role, **kwargs})

    def _result(
        self,
        family: str,
        role: str,
        *,
        text: str = "",
        parsed: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "model": family,
            "role": role,
            "text": text,
            "parsed": parsed,
            "provider": "mock",
            "model_key": "mock",
            "is_mock": True,
            "degraded": False,
            "fallback_reason": None,
            "retries": 0,
        }

    def _dispatch(
        self,
        family: str,
        prompt_file: str,
        state: dict[str, Any],
        action: str,
        *,
        role: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self._record(family, action, role, prompt_file=prompt_file)
        if role in self.fail_roles:
            raise LLMCallError(f"mock failure for role={role}", role=role, provider="mock")
        if self.on_call:
            custom = self.on_call(family, action, kwargs)
            if custom is not None:
                return custom
        if role == "narrator":
            return self._result(family, role, text=self.narrator_text)
        if role == "mechanics":
            return self._result(
                family,
                role,
                parsed={"description": "Mock mechanics.", "consequences": ["mock consequence"]},
            )
        if role == "world_arbiter":
            return self._result(
                family,
                role,
                parsed={"consistency_score": 90, "issues_found": []},
            )
        return self._result(family, role, text=f"mock:{action}")

    def call_claude(self, prompt_file: str, state: dict[str, Any], action: str, **kwargs: Any) -> dict[str, Any]:
        role = kwargs.pop("role", "narrator")
        return self._dispatch("claude", prompt_file, state, action, role=role, **kwargs)

    def call_codex(self, prompt_file: str, state: dict[str, Any], action: str, **kwargs: Any) -> dict[str, Any]:
        role = kwargs.pop("role", "mechanics")
        return self._dispatch("codex", prompt_file, state, action, role=role, **kwargs)

    def call_gpt(self, prompt_file: str, state: dict[str, Any], action: str, **kwargs: Any) -> dict[str, Any]:
        role = kwargs.pop("role", "quick_event")
        return self._dispatch("gpt", prompt_file, state, action, role=role, **kwargs)

    def call_model(
        self,
        model: str,
        prompt_file: str | None,
        state: dict[str, Any],
        action: str,
        *,
        role: str,
        route: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        family = model if model in ("claude", "codex", "gpt", "mock") else "claude"
        return self._dispatch(
            family,
            prompt_file or "world_arbiter.md",
            state,
            action,
            role=role,
            route=route,
            **kwargs,
        )
