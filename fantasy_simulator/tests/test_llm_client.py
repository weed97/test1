"""Tests for LLM client retry and mock degradation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.llm.base import LLMMessage, LLMRequest, LLMResponse  # noqa: E402
from utils.llm_errors import LLMCallError  # noqa: E402
from utils.llm_client import LLMClient  # noqa: E402


class LLMClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = LLMClient(ROOT)

    def test_provider_status_shows_mock_without_keys(self) -> None:
        status = self.client.provider_status()
        self.assertFalse(status["any_live_provider"])
        self.assertEqual(status["active_fallback"], "mock")

    def test_degrade_to_mock_on_api_failure(self) -> None:
        from utils.llm.providers.openai import OpenAIProvider

        live_provider = OpenAIProvider(api_key="test-key-for-unit-test")
        resolved = {
            "role": "narrator",
            "model_key": "opus_48_high",
            "model": "claude-opus-4-8",
            "provider": live_provider,
            "structured": False,
            "schema": None,
            "temperature": 0.85,
        }

        with patch.object(self.client.llm_router, "resolve_with_fallback", return_value=resolved):
            with patch.object(
                self.client,
                "_complete_with_retries",
                side_effect=LLMCallError("API down", provider="anthropic"),
            ):
                result = self.client._call(
                    "claude",
                    "narrator_claude.md",
                    {"next_turn": 1},
                    "explore",
                    role="narrator",
                )

        self.assertTrue(result["is_mock"])
        self.assertTrue(result["degraded"])
        self.assertIn("text", result)

    def test_complete_with_retries_raises_after_exhausted(self) -> None:
        class FailProvider:
            name = "fail"

            def complete(self, request: LLMRequest) -> LLMResponse:
                raise RuntimeError("network error")

        with self.assertRaises(LLMCallError):
            self.client._complete_with_retries(FailProvider(), LLMRequest(model="x", messages=[], temperature=0))


if __name__ == "__main__":
    unittest.main()
