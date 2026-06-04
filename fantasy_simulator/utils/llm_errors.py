"""LLM call errors and result helpers."""

from __future__ import annotations


class LLMCallError(RuntimeError):
    """Raised when an LLM provider call fails after retries."""

    def __init__(self, message: str, *, role: str = "", provider: str = "", cause: Exception | None = None):
        super().__init__(message)
        self.role = role
        self.provider = provider
        self.cause = cause
