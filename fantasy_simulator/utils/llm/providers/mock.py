"""Mock LLM provider — deterministic structured output for offline runs."""

from __future__ import annotations

import json
from typing import Any

from utils.llm.base import LLMMessage, LLMProvider, LLMRequest, LLMResponse


class MockProvider:
    name = "mock"

    def is_available(self) -> bool:
        return True

    def complete(self, request: LLMRequest) -> LLMResponse:
        role = request.metadata.get("role", "")
        content = _mock_for_role(role, request)
        parsed = None
        if request.structured:
            parsed = json.loads(content)
        return LLMResponse(
            content=content,
            model="mock",
            provider=self.name,
            parsed=parsed,
        )


def _mock_for_role(role: str, request: LLMRequest) -> str:
    ctx = request.metadata.get("context", {})
    turn = ctx.get("next_turn", 1)

    if role == "world_arbiter":
        payload = {
            "world": ctx.get("world", {}),
            "factions": ctx.get("factions", {}),
            "flags": ctx.get("flags", {}),
            "event_log_append": [
                {
                    "turn": turn,
                    "type": request.metadata.get("action", "explore"),
                    "summary": request.metadata.get("mechanical_summary", "Mock world update."),
                }
            ],
            "narrative_hint": request.metadata.get(
                "mechanical_summary", "Mock narrative hint for the narrator."
            ),
        }
        return json.dumps(payload, ensure_ascii=False)

    if role == "combat_referee":
        mechanical = request.metadata.get("mechanical_result", {})
        payload = {
            "combat_log": mechanical.get("lines", ["Mock combat round."]),
            "combat_state": {
                "round": mechanical.get("round", 1),
                "participants": {},
                "status_effects": {},
            },
            "world_updates": {
                "combat": mechanical.get("combat"),
                "event_log_append": mechanical.get("event_log_append", []),
            },
            "character_updates": mechanical.get("character_updates", {}),
        }
        return json.dumps(payload, ensure_ascii=False)

    if role == "narrator":
        hint = request.metadata.get("narrative_hint", "")
        mech = request.metadata.get("mechanical_summary", "")
        return (
            f"[내레이션]\n{hint or mech or 'Mock narration.'}\n\n"
            f"[상태 요약]\n- Turn {turn}\n- (mock provider)"
        )

    return json.dumps({"message": f"mock response for {role}"}, ensure_ascii=False)
