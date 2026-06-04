"""LLM request/response types and provider protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMRequest:
    model: str
    messages: list[LLMMessage]
    temperature: float = 0.7
    structured: bool = False
    schema_name: str | None = None
    schema: dict[str, Any] | None = None
    max_tokens: int | None = None
    reasoning_effort: str | None = None
    effort: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    raw: dict[str, Any] = field(default_factory=dict)
    parsed: dict[str, Any] | None = None


class LLMProvider(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def complete(self, request: LLMRequest) -> LLMResponse: ...
