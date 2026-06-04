"""Debug / introspection helpers for LLM routing."""

from __future__ import annotations

from typing import Any

from utils.llm_client import LLMClient
from utils.llm_router import (
    _load_routing,
    classify_action_needs,
    decide_model_and_prompt,
    describe_routes,
    route_action,
)


def format_routing_report(state: dict[str, Any], base_dir: Any, *, mode: str = "llm") -> str:
    routing = _load_routing(base_dir)
    lines = [
        "=== Multi-Model Architecture ===",
        "  docs/ARCHITECTURE.md",
        "",
        "=== Call chain (actual) ===",
        "  GameSession.run_turn()",
        "    → turn_processor.execute_turn()",
        "      → process_player_action()  ← action resolution only",
        "",
        "=== Role → Model ===",
        "  서사     → Claude Opus  (narrator_claude.md)",
        "  규칙     → Codex 5.3     (mechanics_codex.md)",
        "  일관성   → Opus          (world_arbiter.md, every 5 turns)",
        "",
        "=== Keyword routing ===",
        "  attack/cast/combat → codex",
        "  explore/talk/look  → claude",
        "  rest / unknown     → rule_based",
        "",
        "=== Action needs (explore) ===",
    ]
    for k, v in classify_action_needs("explore", state).items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    for sample in ("attack goblin", "explore forest", "rest"):
        d = decide_model_and_prompt(sample, state, mode=mode, base_dir=base_dir)
        lines.append(f"  '{sample}' → {d['model']} use_llm={d['use_llm']}")
    lines.extend(["", "=== Config pipeline (explore) ==="])
    sample = route_action("explore", state, mode=mode, base_dir=base_dir)
    lines.extend(f"  {line}" for line in describe_routes(sample))
    interval = routing.get("consistency_check_interval", 5)
    lines.append(f"\nConsistency check: every {interval} turns")
    client = LLMClient(base_dir)
    lines.extend(["", client.format_provider_status()])
    return "\n".join(lines)
