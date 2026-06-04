"""Claude / Codex / GPT API call helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.io_helpers import load_text
from utils.llm.base import LLMMessage, LLMRequest
from utils.llm.router import LLMRouter
from utils.structured_output import StructuredOutputClient, StructuredOutputError


class LLMClient:
    """Thin wrapper around providers + structured output validation."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir)
        self.llm_router = LLMRouter(self.base_dir)
        so_cfg = self.llm_router.structured_config()
        self.structured = StructuredOutputClient(
            schemas_dir=self.base_dir / "schemas",
            max_retries=so_cfg.get("max_retries", 3),
            repair_on_failure=so_cfg.get("repair_on_failure", True),
        )

    def load_prompt(self, prompt_file: str) -> str:
        path = self.base_dir / "prompts" / prompt_file
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return load_text(path)

    def call_claude(
        self,
        prompt_file: str,
        state: dict[str, Any],
        action: str,
        *,
        role: str = "narrator",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._call("claude", prompt_file, state, action, role=role, metadata=metadata)

    def call_codex(
        self,
        prompt_file: str,
        state: dict[str, Any],
        action: str,
        *,
        role: str = "mechanics",
        metadata: dict[str, Any] | None = None,
        rules: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        extra = metadata or {}
        if rules:
            extra = {**extra, "rules": rules}
        return self._call("codex", prompt_file, state, action, role=role, metadata=extra)

    def call_gpt(
        self,
        prompt_file: str,
        state: dict[str, Any],
        action: str,
        *,
        role: str = "quick_event",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._call("gpt", prompt_file, state, action, role=role, metadata=metadata)

    def call_model(
        self,
        model: str,
        prompt_file: str | None,
        state: dict[str, Any],
        action: str,
        *,
        role: str,
        route: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        rules: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if model == "rule":
            raise ValueError("Use run_rule_based for model=rule")
        if not prompt_file:
            raise ValueError(f"prompt_file required for model={model}")

        meta = metadata or {}
        if model == "claude":
            return self.call_claude(prompt_file, state, action, role=role, metadata=meta)
        if model == "codex":
            return self.call_codex(prompt_file, state, action, role=role, metadata=meta, rules=rules)
        if model in ("gpt", "mock"):
            return self._call(model, prompt_file, state, action, role=role, metadata=meta, route=route)
        raise ValueError(f"Unknown model family: {model}")

    def _call(
        self,
        family: str,
        prompt_file: str,
        state: dict[str, Any],
        action: str,
        *,
        role: str,
        metadata: dict[str, Any] | None = None,
        route: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        route = route or {"role": role, "schema": None, "structured": False, "temperature": 0.7}
        resolved = self.llm_router.resolve_with_fallback(role)
        is_mock = resolved["model_key"] == self.llm_router.fallback_model()

        system_prompt = self.load_prompt(prompt_file)
        user_payload: dict[str, Any] = {
            "state": state,
            "action": action,
            "metadata": metadata or {},
        }
        if metadata and metadata.get("rules"):
            user_payload["rules"] = metadata["rules"]

        schema_name = route.get("schema") or resolved.get("schema")
        structured = route.get("structured", resolved.get("structured", False))
        if structured and schema_name:
            user_payload["output_schema"] = self.structured.load_schema(schema_name)

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=json.dumps(user_payload, ensure_ascii=False, indent=2)),
        ]

        schema_obj = self.structured.load_schema(schema_name) if structured and schema_name else None
        request = LLMRequest(
            model=resolved["model"],
            messages=messages,
            temperature=route.get("temperature") or resolved["temperature"],
            structured=structured,
            schema_name=schema_name,
            schema=schema_obj,
            max_tokens=resolved.get("max_tokens"),
            reasoning_effort=resolved.get("reasoning_effort"),
            effort=resolved.get("effort"),
            metadata={"role": role, "action": action, "context": state, **(metadata or {})},
        )

        provider = resolved["provider"]
        retries = 0
        last_raw = ""
        while retries <= self.structured.max_retries:
            response = provider.complete(request)
            last_raw = response.content
            if not structured:
                return {
                    "model": family,
                    "role": role,
                    "text": response.content,
                    "parsed": None,
                    "provider": provider.name,
                    "model_key": resolved["model_key"],
                    "is_mock": is_mock,
                    "retries": retries,
                }
            try:
                parsed = self.structured.parse_and_validate(response.content, schema_name)
                return {
                    "model": family,
                    "role": role,
                    "text": response.content,
                    "parsed": parsed,
                    "provider": provider.name,
                    "model_key": resolved["model_key"],
                    "is_mock": is_mock,
                    "retries": retries,
                }
            except StructuredOutputError as exc:
                retries += 1
                if not self.structured.repair_on_failure or retries > self.structured.max_retries:
                    raise
                repair = self.structured.build_repair_prompt(
                    schema_name, last_raw, exc.errors or [str(exc)]
                )
                request.messages.append(LLMMessage(role="assistant", content=last_raw))
                request.messages.append(LLMMessage(role="user", content=repair))

        raise StructuredOutputError("Structured output retries exhausted", raw=last_raw)

    def provider_status(self) -> dict[str, Any]:
        """Report which configured models can reach live APIs vs mock fallback."""
        models: dict[str, Any] = {}
        for key, cfg in self.llm_router.routing.get("models", {}).items():
            provider_name = cfg.get("provider", "unknown")
            if provider_name == "mock":
                models[key] = {
                    "label": cfg.get("label", key),
                    "provider": "mock",
                    "available": True,
                    "live": False,
                }
                continue
            provider = self.llm_router.provider_for_model(key)
            live = provider.is_available()
            models[key] = {
                "label": cfg.get("label", key),
                "provider": provider_name,
                "model": cfg.get("model"),
                "available": live,
                "live": live,
            }
        fallback = self.llm_router.fallback_model()
        any_live = any(m.get("live") for m in models.values())
        return {
            "any_live_provider": any_live,
            "active_fallback": fallback,
            "note": (
                "Live API keys detected — real providers will be used."
                if any_live
                else "No API keys — all roles fall back to mock provider."
            ),
            "models": models,
        }

    def format_provider_status(self) -> str:
        status = self.provider_status()
        lines = [
            "=== LLM Provider Status ===",
            f"  {status['note']}",
            f"  fallback: {status['active_fallback']}",
            "",
        ]
        for key, info in status["models"].items():
            tag = "live" if info.get("live") else "mock/offline"
            lines.append(f"  {info['label']} ({key}): {tag}")
        return "\n".join(lines)


def call_claude(
    client: LLMClient,
    prompt_file: str,
    state: dict[str, Any],
    action: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return client.call_claude(prompt_file, state, action, **kwargs)


def call_codex(
    client: LLMClient,
    prompt_file: str,
    state: dict[str, Any],
    action: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return client.call_codex(prompt_file, state, action, **kwargs)


def call_gpt(
    client: LLMClient,
    prompt_file: str,
    state: dict[str, Any],
    action: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return client.call_gpt(prompt_file, state, action, **kwargs)
