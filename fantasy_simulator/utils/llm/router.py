"""Route roles to model-specific LLM providers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.io_helpers import load_json
from utils.llm.base import LLMProvider
from utils.llm.providers.anthropic import AnthropicProvider
from utils.llm.providers.mock import MockProvider
from utils.llm.providers.openai import OpenAIProvider


class LLMRouter:
    def __init__(self, base_dir: Path, routing: dict[str, Any] | None = None) -> None:
        self.base_dir = Path(base_dir)
        self.routing = routing or load_json(self.base_dir / "config" / "llm_routing.json")
        self._providers: dict[str, LLMProvider] = {}

    def provider_for_model(self, model_key: str) -> LLMProvider:
        if model_key in self._providers:
            return self._providers[model_key]

        cfg = self.routing["models"][model_key]
        provider_name = cfg["provider"]
        if provider_name == "mock":
            provider = MockProvider()
        elif provider_name == "anthropic":
            provider = AnthropicProvider()
        elif provider_name == "openai":
            provider = OpenAIProvider()
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

        self._providers[model_key] = provider
        return provider

    def model_config(self, model_key: str) -> dict[str, Any]:
        return self.routing["models"][model_key]

    def resolve_role(self, role: str, *, force_model_key: str | None = None) -> dict[str, Any]:
        role_cfg = self.routing["roles"][role]
        model_key = force_model_key or role_cfg["model"]
        model_cfg = self.routing["models"][model_key]
        provider = self.provider_for_model(model_key)
        return {
            "role": role,
            "model_key": model_key,
            "model_label": model_cfg.get("label", model_key),
            "model": model_cfg.get("model", model_key),
            "provider": provider,
            "structured": role_cfg.get("structured", False),
            "schema": role_cfg.get("schema"),
            "temperature": role_cfg.get(
                "temperature", model_cfg.get("temperature_default", 0.7)
            ),
            "max_tokens": model_cfg.get("max_tokens"),
            "reasoning_effort": model_cfg.get("reasoning_effort"),
            "effort": model_cfg.get("effort"),
        }

    def resolve_with_fallback(self, role: str) -> dict[str, Any]:
        resolved = self.resolve_role(role)
        model_key = resolved["model_key"]
        provider = resolved["provider"]
        fallback = self.fallback_model()

        if not provider.is_available() and model_key != fallback:
            resolved = self.resolve_role(role, force_model_key=fallback)
        return resolved

    def fallback_model(self) -> str:
        return self.routing.get("default_model", "mock")

    def structured_config(self) -> dict[str, Any]:
        return self.routing.get("structured_output", {})

    def hybrid_pipeline(self, action: str) -> list[str] | None:
        return self.routing.get("hybrid_overrides", {}).get(action)
