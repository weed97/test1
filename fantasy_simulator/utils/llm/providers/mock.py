"""Mock LLM provider — deterministic structured output for offline runs."""

from __future__ import annotations

import json

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
    action = request.metadata.get("action", "explore")

    if role == "quick_event":
        summary = mech or "A quiet moment passes in Eldoria."
        payload = {
            "event_title": "Whispers in the alley",
            "description": summary,
            "potential_consequences": ["investigate", "move on"],
            "suggested_state_changes": {},
        }
        return json.dumps(payload, ensure_ascii=False)

    if role == "mechanics":
        mechanical = request.metadata.get("mechanical_result", {})
        result_type = "combat" if ctx.get("combat") else action if action in ("rest", "explore") else "event"
        if result_type == "explore":
            result_type = "exploration"
        lines = mechanical.get("lines", [])
        desc = mechanical.get("summary") or mech or "Mechanical resolution."
        payload = {
            "result_type": result_type,
            "success": True,
            "description": desc,
            "state_changes": {
                "event_log_append": [
                    {"turn": turn, "type": result_type, "summary": desc}
                ]
            },
            "consequences": lines or [desc],
        }
        if mechanical.get("character_updates"):
            payload["state_changes"]["character_updates"] = mechanical["character_updates"]
        if mechanical.get("combat") is not None or "combat" in mechanical:
            payload["state_changes"]["combat"] = mechanical.get("combat")
        return json.dumps(payload, ensure_ascii=False)

    if role == "world_arbiter":
        payload = {
            "consistency_score": 8,
            "issues_found": [],
            "recommended_corrections": [],
            "narrative_direction_suggestion": "Maintain rising tension toward the shadow legion threat.",
        }
        return json.dumps(payload, ensure_ascii=False)

    if role == "narrator":
        hint = request.metadata.get("narrative_hint", "")
        qe = request.metadata.get("quick_event") or {}
        if not hint and qe:
            hint = qe.get("description", "")
        body = hint or mech or "The party presses onward through Eldoria."
        return (
            f"The wind carried the scent of old stone and distant rain. {body}\n\n"
            f"Elara lowered her voice. \"Stay close. The road remembers more than we do.\"\n\n"
            f"Gareth nodded, hand resting on his sword. \"Then we make our own path.\""
        )

    return json.dumps({"message": f"mock response for {role}"}, ensure_ascii=False)
