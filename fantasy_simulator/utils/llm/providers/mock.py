"""Mock LLM provider — deterministic structured output for offline runs."""

from __future__ import annotations

import json
from typing import Any

from utils.llm.base import LLMRequest, LLMResponse


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
    mech = request.metadata.get("mechanical_summary", "")

    if role == "event_alternatives":
        base = mech or "주변을 정찰한다."
        payload = {
            "alternatives": [
                {"id": "a", "summary": base, "risk": "low", "tone": "calm"},
                {
                    "id": "b",
                    "summary": "낯선 발소리가 폐허 저편에서 들린다.",
                    "risk": "medium",
                    "tone": "tense",
                },
            ],
            "recommended_id": "a",
            "narrative_hint": base or "Mock event hint.",
        }
        return json.dumps(payload, ensure_ascii=False)

    if role == "world_arbiter":
        alts = request.metadata.get("event_alternatives") or {}
        hint = alts.get("narrative_hint") or mech or "Mock world update."
        payload = {
            "world": ctx.get("world", {}),
            "factions": ctx.get("factions", {}),
            "flags": ctx.get("flags", {}),
            "event_log_append": [
                {
                    "turn": turn,
                    "type": request.metadata.get("action", "explore"),
                    "summary": hint,
                }
            ],
            "narrative_hint": hint,
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
        alts = request.metadata.get("event_alternatives") or {}
        if not hint and alts:
            hint = alts.get("narrative_hint", "")
        body = hint or mech or "Mock narration."
        return (
            f"[내레이션]\n{body}\n\n"
            f"엘라라: \"조심해, 이 근처는 뭔가 수상해.\"\n\n"
            f"[상태 요약]\n- Turn {turn}\n- (mock / opus placeholder)"
        )

    return json.dumps({"message": f"mock response for {role}"}, ensure_ascii=False)
