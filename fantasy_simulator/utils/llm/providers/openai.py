"""OpenAI / Codex provider (optional — requires OPENAI_API_KEY)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from utils.llm.base import LLMProvider, LLMRequest, LLMResponse


class OpenAIProvider:
    name = "openai"
    api_url = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("OPENAI_API_KEY not set")

        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        body: dict = {
            "model": request.model,
            "temperature": request.temperature,
            "messages": messages,
        }

        if request.structured and request.schema:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.schema_name or "output",
                    "strict": True,
                    "schema": _openai_schema(request.schema),
                },
            }

        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error {exc.code}: {detail}") from exc

        text = raw["choices"][0]["message"]["content"]
        return LLMResponse(content=text or "{}", model=request.model, provider=self.name, raw=raw)


def _openai_schema(schema: dict) -> dict:
    """OpenAI strict mode rejects some JSON Schema keywords — strip them."""
    cleaned = dict(schema)
    cleaned.pop("$schema", None)
    cleaned.pop("title", None)
    return cleaned
