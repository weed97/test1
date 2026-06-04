"""Single entry point for resolving one player action (rule / LLM)."""

from __future__ import annotations

from typing import Any, Literal

from utils.llm_client import LLMClient
from utils.llm_router import decide_model_and_prompt, route_consistency_check
from utils.rule_engine import RuleEngine
from utils.state_manager import StateManager

Mode = Literal["rule", "llm", "hybrid"]

PROMPT_NARRATOR = "narrator_claude.md"
PROMPT_MECHANICS = "mechanics_codex.md"
PROMPT_WORLD_ARBITER = "world_arbiter.md"
PROMPT_QUICK_EVENT = "quick_event_gpt.md"


def run_rule_engine(
    rules: RuleEngine,
    loader: Any,
    state: dict[str, Any],
    action: str,
    turn: int,
) -> dict[str, Any]:
    """Rule-based resolution (combat round, explore, rest)."""
    if state.get("combat") or action == "combat":
        return rules.run_combat_round(turn)
    if action == "explore":
        return rules.run_exploration(turn)
    if action == "rest":
        return rules.run_rest(turn, loader)
    return {"summary": f"Unknown action: {action}", "event_log_append": []}


def _rule_result(mechanical: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": "rule",
        "role": "rule_engine",
        "mechanical": mechanical,
        "parsed": None,
        "text": "",
    }


def _append_rule_outcome(mechanical: dict[str, Any], lines: list[str]) -> None:
    lines.extend(mechanical.get("lines", []))
    if mechanical.get("summary") and not mechanical.get("lines"):
        lines.append(mechanical["summary"])


def _normalize_prompt_file(prompt_file: str | None, default: str) -> str:
    if not prompt_file:
        return default
    return prompt_file.replace("prompts/", "")


def _invoke_llm(
    client: LLMClient,
    *,
    model: str,
    role: str,
    prompt_file: str | None,
    snapshot: dict[str, Any],
    action: str,
    metadata: dict[str, Any],
    rules_text: dict[str, str] | None,
) -> dict[str, Any]:
    pf = _normalize_prompt_file(prompt_file, PROMPT_NARRATOR)
    if model == "claude":
        return client.call_claude(pf, snapshot, action, role="narrator", metadata=metadata)
    if model == "codex":
        if rules_text is None:
            raise ValueError("rules_text required for codex")
        pf = _normalize_prompt_file(prompt_file, PROMPT_MECHANICS)
        return client.call_codex(pf, snapshot, action, role="mechanics", rules=rules_text, metadata=metadata)
    if model == "gpt":
        pf = _normalize_prompt_file(prompt_file, PROMPT_QUICK_EVENT)
        return client.call_gpt(pf, snapshot, action, role="quick_event", metadata=metadata)
    raise ValueError(f"Unsupported LLM model family: {model}")


def process_player_action(
    state: dict[str, Any],
    action: str,
    *,
    mode: Mode,
    turn: int,
    manager: StateManager,
    rules: RuleEngine,
    client: LLMClient | None,
) -> dict[str, Any]:
    """Route action → rule engine and/or LLM → persist via StateManager."""
    decision = decide_model_and_prompt(action, state, mode=mode, base_dir=manager.base_dir)
    snapshot = manager.snapshot()
    outcome_lines: list[str] = [
        f"routing: model={decision['model']} priority={decision.get('priority')} "
        f"prompt={decision.get('prompt_file')}",
    ]
    results: list[dict[str, Any]] = []
    rules_text: dict[str, str] | None = None

    if mode == "hybrid":
        mechanical = run_rule_engine(rules, manager.loader, state, action, turn)
        result = _rule_result(mechanical)
        manager.apply_result(state, result, turn=turn)
        results.append(result)
        _append_rule_outcome(mechanical, outcome_lines)

    if not decision["use_llm"] or client is None:
        if mode != "hybrid":
            mechanical = run_rule_engine(rules, manager.loader, state, action, turn)
            result = _rule_result(mechanical)
            manager.apply_result(state, result, turn=turn)
            results.append(result)
            _append_rule_outcome(mechanical, outcome_lines)
        manager.save(state)
        manager.refresh_state(state)
        return {"decision": decision, "results": results, "lines": outcome_lines}

    pipeline = decision.get("pipeline") or []
    llm_steps = [s for s in pipeline if s.get("model") != "rule"]
    if not llm_steps:
        llm_steps = [
            {
                "model": decision["model"],
                "role": decision.get("role"),
                "prompt_file": decision.get("prompt_file"),
            }
        ]

    narrative_hint = ""
    for step in llm_steps:
        model = step.get("model") or decision["model"]
        metadata: dict[str, Any] = {"narrative_hint": narrative_hint}

        if model == "codex" and rules_text is None:
            rules_text = {
                "combat": manager.loader.load_rule("combat"),
                "magic_system": manager.loader.load_rule("magic_system"),
            }

        try:
            result = _invoke_llm(
                client,
                model=model,
                role=step.get("role") or decision.get("role") or "narrator",
                prompt_file=step.get("prompt_file") or decision.get("prompt_file"),
                snapshot=snapshot,
                action=action,
                metadata=metadata,
                rules_text=rules_text,
            )
        except ValueError:
            mechanical = run_rule_engine(rules, manager.loader, state, action, turn)
            result = _rule_result(mechanical)

        manager.apply_result(state, result, turn=turn)
        results.append(result)

        if result.get("parsed"):
            parsed = result["parsed"]
            narrative_hint = parsed.get("description", narrative_hint)
            if step.get("role") == "mechanics":
                outcome_lines.append(parsed.get("description", ""))
                outcome_lines.extend(parsed.get("consequences", []))

        if result.get("text") and step.get("role") == "narrator":
            outcome_lines.append(result["text"])

        provider = result.get("provider", "?")
        mock_tag = " [mock]" if result.get("is_mock") else ""
        outcome_lines.append(f"{step.get('role', model)} [{model}/{provider}{mock_tag}]")

    if mode in ("llm", "hybrid") and client is not None:
        for step in route_consistency_check(turn, state, base_dir=manager.base_dir):
            result = client.call_model(
                step["model"],
                PROMPT_WORLD_ARBITER,
                snapshot,
                "consistency_check",
                role="world_arbiter",
                route=step,
            )
            manager.apply_result(state, result, turn=turn)
            if result.get("parsed"):
                p = result["parsed"]
                outcome_lines.append(
                    f"[world_arbiter] score={p.get('consistency_score')} "
                    f"issues={len(p.get('issues_found', []))}"
                )

    manager.save(state)
    manager.refresh_state(state)
    return {"decision": decision, "results": results, "lines": outcome_lines}
