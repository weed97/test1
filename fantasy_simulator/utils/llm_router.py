"""Decide which model/prompt pipeline to use for each action."""

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


def route_action(
    action: str,
    state: dict[str, Any],
    *,
    mode: str = "llm",
    turn: int = 1,
    base_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Return ordered LLM/rule steps for one turn action.

    Example return value:
        [
            {"model": "gpt", "role": "quick_event", "prompt_file": "quick_event_gpt.md", ...},
            {"model": "codex", "role": "mechanics", "prompt_file": "mechanics_codex.md", ...},
            {"model": "claude", "role": "narrator", "prompt_file": "narrator_claude.md", ...},
        ]
    """
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

    # llm mode
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


def describe_routes(routes: list[dict[str, Any]]) -> list[str]:
    return [
        f"{s.get('role', '?')} [{s.get('model', '?')}]"
        + (f" ← {s['prompt_file']}" if s.get("prompt_file") else "")
        for s in routes
    ]
