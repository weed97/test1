"""Decide which model/prompt to use for each player action."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.io_helpers import load_json

# Config model keys → simplified family names used by simulation_engine / llm_client
MODEL_FAMILY: dict[str, str] = {
    "opus_48_high": "claude",
    "codex_53": "codex",
    "gpt_55_high": "gpt",
    "mock": "mock",
}

ROLE_PROMPTS: dict[str, str] = {
    "narrator": "narrator_claude.md",
    "mechanics": "mechanics_codex.md",
    "world_arbiter": "world_arbiter.md",
    "quick_event": "quick_event_gpt.md",
}

MECHANICS_KEYWORDS = ("fight", "attack", "cast", "magic", "combat", "damage")
NARRATIVE_KEYWORDS = ("talk", "look", "explore", "describe", "check", "investigate")


def _load_routing(base_dir: Path | None = None) -> dict[str, Any]:
    root = base_dir or Path(__file__).resolve().parent.parent
    return load_json(root / "config" / "llm_routing.json")


def _resolve_pipeline_action(action: str, *, in_combat: bool) -> str:
    if in_combat or action == "combat":
        return "combat_round"
    if action == "combat_start":
        return "combat_start"
    return action


def _role_to_step(role: str, routing: dict[str, Any]) -> dict[str, Any]:
    role_cfg = routing["roles"][role]
    model_key = role_cfg["model"]
    family = MODEL_FAMILY.get(model_key, model_key)
    prompt_file = role_cfg.get("prompt") or ROLE_PROMPTS.get(role, f"{role}.md")
    return {
        "model": family,
        "model_key": model_key,
        "role": role,
        "prompt_file": prompt_file,
        "structured": role_cfg.get("structured", False),
        "schema": role_cfg.get("schema"),
        "temperature": role_cfg.get("temperature"),
    }


def decide_model_and_prompt(
    action: str,
    state: dict[str, Any],
    *,
    mode: str = "llm",
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Minimal keyword router for process_player_action().

    Returns:
        {
            "use_llm": bool,
            "model": "claude" | "codex" | "rule_based",
            "prompt_file": str | None,
            "priority": "strict_rules" | "immersion" | "simple",
            "pipeline": list[dict],  # single-step or multi-step for advanced modes
        }
    """
    if mode == "rule":
        return {
            "use_llm": False,
            "model": "rule_based",
            "prompt_file": None,
            "priority": "simple",
            "pipeline": [{"model": "rule", "role": "rule_engine", "prompt_file": None}],
        }

    action_lower = action.lower()
    in_combat = bool(state.get("combat"))

    # Active combat or rules-heavy keywords → Codex
    if in_combat or any(kw in action_lower for kw in MECHANICS_KEYWORDS):
        return _mechanics_decision(base_dir)

    # Narrative / immersion keywords → Claude
    if any(kw in action_lower for kw in NARRATIVE_KEYWORDS):
        return _narrator_decision(base_dir)

    # Default: rule-based
    return {
        "use_llm": False,
        "model": "rule_based",
        "prompt_file": None,
        "priority": "simple",
        "pipeline": [{"model": "rule", "role": "rule_engine", "prompt_file": None}],
    }


def _mechanics_decision(base_dir: Path | None) -> dict[str, Any]:
    step = _role_to_step("mechanics", _load_routing(base_dir))
    return {
        "use_llm": True,
        "model": "codex",
        "prompt_file": "prompts/mechanics_codex.md",
        "priority": "strict_rules",
        "role": "mechanics",
        "structured": True,
        "schema": "mechanics_codex",
        "pipeline": [step],
    }


def _narrator_decision(base_dir: Path | None) -> dict[str, Any]:
    step = _role_to_step("narrator", _load_routing(base_dir))
    return {
        "use_llm": True,
        "model": "claude",
        "prompt_file": "prompts/narrator_claude.md",
        "priority": "immersion",
        "role": "narrator",
        "structured": False,
        "schema": None,
        "pipeline": [step],
    }


def route_action(
    action: str,
    state: dict[str, Any],
    *,
    mode: str = "llm",
    turn: int = 1,
    base_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Return ordered LLM/rule steps for one turn action (config pipeline)."""
    routing = _load_routing(base_dir)
    in_combat = bool(state.get("combat"))
    pipeline_key = _resolve_pipeline_action(action, in_combat=in_combat)

    if mode == "rule":
        return [{"model": "rule", "role": "rule_engine", "prompt_file": None}]

    if mode == "hybrid":
        steps: list[dict[str, Any]] = [{"model": "rule", "role": "rule_engine", "prompt_file": None}]
        roles = routing.get("hybrid_overrides", {}).get(pipeline_key)
        if roles:
            steps.extend(_role_to_step(r, routing) for r in roles)
        return steps

    roles = routing.get("pipelines", {}).get(pipeline_key, ["narrator"])
    return [_role_to_step(r, routing) for r in roles]


def route_consistency_check(
    turn: int,
    state: dict[str, Any],
    *,
    base_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """World arbiter consistency pass — every N turns."""
    routing = _load_routing(base_dir)
    interval = routing.get("consistency_check_interval", 5)
    if interval <= 0 or turn % interval != 0:
        return []
    roles = routing.get("pipelines", {}).get("consistency_check", ["world_arbiter"])
    return [_role_to_step(r, routing) for r in roles]


def classify_action_needs(
    action: str,
    state: dict[str, Any],
) -> dict[str, bool]:
    """What model capabilities does this action require?"""
    decision = decide_model_and_prompt(action, state, mode="llm")
    in_combat = bool(state.get("combat"))
    return {
        "narrative": decision["model"] == "claude" or action in ("explore", "rest", "combat_start") or in_combat,
        "mechanics": decision["model"] == "codex" or in_combat,
        "quick_ideas": False,
        "consistency_check": False,
    }


def describe_routes(routes: list[dict[str, Any]]) -> list[str]:
    return [
        f"{s.get('role', '?')} [{s.get('model', '?')}]"
        + (f" ← {s['prompt_file']}" if s.get("prompt_file") else "")
        for s in routes
    ]
