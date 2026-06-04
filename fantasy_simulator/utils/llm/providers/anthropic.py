"""Anthropic Claude provider (optional — requires ANTHROPIC_API_KEY)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from utils.llm.base import LLMProvider, LLMRequest, LLMResponse


class AnthropicProvider:
    name = "anthropic"
    api_url = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("ANTHROPIC_API_KEY not set")

        system_parts = [m.content for m in request.messages if m.role == "system"]
        user_messages = []
        for m in request.messages:
            if m.role == "system":
                continue
            user_messages.append({"role": m.role, "content": m.content})

        max_tokens = request.max_tokens or 4096
        body: dict = {
            "model": request.model,
            "max_tokens": max_tokens,
            "temperature": request.temperature,
            "system": "\n\n".join(system_parts),
            "messages": user_messages,
        }

        if request.effort == "high":
            body["thinking"] = {"type": "enabled", "budget_tokens": min(10000, max_tokens // 2)}

        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API error {exc.code}: {detail}") from exc

        text = "".join(
            block.get("text", "")
            for block in raw.get("content", [])
            if block.get("type") == "text"
        )
        return LLMResponse(content=text, model=request.model, provider=self.name, raw=raw)
