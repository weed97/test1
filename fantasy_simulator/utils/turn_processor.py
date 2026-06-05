"""Single entry point for resolving one player action (rule / LLM)."""

from __future__ import annotations

import copy
from typing import Any

from utils.llm_errors import LLMCallError
from utils.llm_router import decide_model_and_prompt, route_consistency_check
from utils.temporal import format_moment_label, resolve_time_steps, somatic_presence_line
from utils.turn_context import TurnContext, TurnResult

PROMPT_NARRATOR = "narrator_claude.md"
PROMPT_MECHANICS = "mechanics_codex.md"
PROMPT_WORLD_ARBITER = "world_arbiter.md"
PROMPT_QUICK_EVENT = "quick_event_gpt.md"


def run_rule_engine(ctx: TurnContext) -> dict[str, Any]:
    """Rule-based resolution: combat, explore, social, investigate, rest."""
    state, action, turn = ctx.state, ctx.action, ctx.turn
    rules, loader = ctx.rules, ctx.manager.loader

    if state.get("combat") or action == "combat":
        return rules.run_combat_round(turn)

    lower = action.lower().strip()
    if lower.startswith("talk") or lower.startswith("speak") or "대화" in action:
        return rules.run_social(action, turn, loader)
    if lower.startswith("investigate") or lower.startswith("inspect") or "조사" in action:
        return rules.run_investigate(action, turn)
    if lower in ("quest", "quests", "퀘스트") or lower.startswith("quest "):
        return rules.run_quest_status()
    if lower == "explore" or "explore" in lower or "탐험" in action:
        return rules.run_exploration(turn)
    if lower == "rest" or "휴식" in action:
        return rules.run_rest(turn, loader)

    if rules.event_engine:
        triggered = rules.event_engine.try_trigger_event(state, "explore", turn)
        if triggered:
            return triggered
    return {"summary": f"'{action}' — 알 수 없는 행동.", "event_log_append": []}


def _rule_result(mechanical: dict[str, Any], *, reason: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "model": "rule",
        "role": "rule_engine",
        "mechanical": mechanical,
        "parsed": None,
        "text": "",
    }
    if reason:
        out["fallback_reason"] = reason
    return out


def _append_rule_outcome(mechanical: dict[str, Any], lines: list[str]) -> None:
    lines.extend(mechanical.get("lines", []))
    if mechanical.get("summary") and not mechanical.get("lines"):
        lines.append(mechanical["summary"])


def _normalize_prompt_file(prompt_file: str | None, default: str) -> str:
    if not prompt_file:
        return default
    return prompt_file.replace("prompts/", "")


def _apply_rule_turn(
    ctx: TurnContext,
    *,
    results: list[dict[str, Any]],
    outcome_lines: list[str],
    reason: str | None = None,
) -> None:
    mechanical = run_rule_engine(ctx)
    result = _rule_result(mechanical, reason=reason)
    ctx.manager.apply_result(ctx.state, result, turn=ctx.turn)
    results.append(result)
    _append_rule_outcome(mechanical, outcome_lines)
    if reason:
        outcome_lines.append(f"⚠ LLM 대신 규칙 엔진으로 처리했습니다: {reason}")


def _invoke_llm(ctx: TurnContext, *, model: str, prompt_file: str | None, metadata: dict[str, Any], rules_text: dict[str, str] | None, route: dict[str, Any] | None) -> dict[str, Any]:
    client = ctx.client
    if client is None:
        raise ValueError("LLM client not configured")
    snapshot = ctx.manager.snapshot()
    pf = _normalize_prompt_file(prompt_file, PROMPT_NARRATOR)
    if model == "claude":
        return client.call_claude(pf, snapshot, ctx.action, role="narrator", metadata=metadata, route=route)
    if model == "codex":
        if rules_text is None:
            raise ValueError("rules_text required for codex")
        pf = _normalize_prompt_file(prompt_file, PROMPT_MECHANICS)
        return client.call_codex(pf, snapshot, ctx.action, role="mechanics", rules=rules_text, metadata=metadata, route=route)
    if model == "gpt":
        pf = _normalize_prompt_file(prompt_file, PROMPT_QUICK_EVENT)
        return client.call_gpt(pf, snapshot, ctx.action, role="quick_event", metadata=metadata, route=route)
    raise ValueError(f"Unsupported LLM model family: {model}")


def _format_llm_line(step: dict[str, Any], result: dict[str, Any]) -> str:
    model = step.get("model") or result.get("model", "?")
    provider = result.get("provider", "?")
    tags: list[str] = []
    if result.get("is_mock"):
        tags.append("mock")
    if result.get("degraded"):
        tags.append("degraded")
    tag_str = f" [{','.join(tags)}]" if tags else ""
    return f"{step.get('role', model)} [{model}/{provider}{tag_str}]"


def process_player_action(ctx: TurnContext) -> dict[str, Any]:
    """Route action → rule engine and/or LLM → persist. Action resolution only (no time advance)."""
    state, action, mode = ctx.state, ctx.action, ctx.mode
    manager, rules, client, turn = ctx.manager, ctx.rules, ctx.client, ctx.turn

    decision = decide_model_and_prompt(action, state, mode=mode, base_dir=manager.base_dir)
    outcome_lines: list[str] = [
        f"routing: model={decision['model']} priority={decision.get('priority')} "
        f"prompt={decision.get('prompt_file')}",
    ]
    results: list[dict[str, Any]] = []
    rules_text: dict[str, str] | None = None

    if mode == "hybrid":
        _apply_rule_turn(ctx, results=results, outcome_lines=outcome_lines)

    if not decision["use_llm"] or client is None:
        if mode != "hybrid":
            _apply_rule_turn(ctx, results=results, outcome_lines=outcome_lines)
        manager.save(state)
        manager.refresh_state(state)
        return {"decision": decision, "results": results, "lines": outcome_lines}

    pipeline = decision.get("pipeline") or []
    llm_steps = [s for s in pipeline if s.get("model") != "rule"]
    if not llm_steps:
        llm_steps = [{"model": decision["model"], "role": decision.get("role"), "prompt_file": decision.get("prompt_file")}]

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
                ctx,
                model=model,
                prompt_file=step.get("prompt_file") or decision.get("prompt_file"),
                metadata=metadata,
                rules_text=rules_text,
                route=step,
            )
        except (LLMCallError, ValueError) as exc:
            _apply_rule_turn(ctx, results=results, outcome_lines=outcome_lines, reason=str(exc))
            continue

        if result.get("degraded") and result.get("fallback_reason"):
            outcome_lines.append(f"[llm_degraded] {result['fallback_reason']}")

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

        outcome_lines.append(_format_llm_line(step, result))

    if mode in ("llm", "hybrid") and client is not None:
        snapshot = manager.snapshot()
        for step in route_consistency_check(turn, state, base_dir=manager.base_dir):
            try:
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
            except LLMCallError as exc:
                outcome_lines.append(f"[world_arbiter skipped] {exc}")

    manager.save(state)
    manager.refresh_state(state)
    return {"decision": decision, "results": results, "lines": outcome_lines}


def _advance_world_time(ctx: TurnContext) -> tuple[str, int, str]:
    """Apply temporal model; return (time_label, steps_applied, moment_kind)."""
    steps, kind, rest_until_morning = resolve_time_steps(
        ctx.action,
        temporal_mode=ctx.temporal_mode,
        time_scale=ctx.time_scale,
    )
    if rest_until_morning:
        label = ctx.rules.advance_time_to_morning()
        return label, 0, kind
    if steps > 0:
        label = ctx.rules.advance_time(steps=steps)
    else:
        label = ctx.state["world"].get("time_of_day", "afternoon")
    return label, steps, kind


def execute_turn(
    ctx: TurnContext,
    *,
    loader: Any,
    enemy_id: str | None = None,
) -> TurnResult:
    """Full turn: advance time, optional combat start, then process_player_action."""
    from utils.cli import resolve_enemy_id

    time_label, time_steps, moment_kind = _advance_world_time(ctx)
    lines: list[str] = []
    moment_note = format_moment_label(moment_kind, temporal_mode=ctx.temporal_mode)
    if moment_note:
        lines.append(moment_note)
    if ctx.include_presence and ctx.temporal_mode == "nex":
        somatic = somatic_presence_line(ctx.state, rng=getattr(ctx.rules, "rng", None))
        if somatic:
            lines.append(somatic)
    action = ctx.action

    is_combat_start = action.lower().strip().startswith("combat") or action == "combat"
    if is_combat_start and not ctx.state.get("combat"):
        if enemy_id is None:
            parts = action.split(maxsplit=1)
            enemy_id = resolve_enemy_id(
                parts[1] if len(parts) > 1 else "malachar",
                loader.base_dir,
            )
        enemy = copy.deepcopy(loader.load_character(enemy_id))
        party = [copy.deepcopy(c) for c in loader.load_party(ctx.state)]
        ctx.rules.start_combat(enemy, party, ctx.turn)
        ctx.manager.append_event(
            {"turn": ctx.turn, "type": "combat_start", "summary": f"전투 시작: {enemy['name']}"},
            ctx.state,
        )
        lines.append(f"전투가 시작되었다. (적: {enemy_id})")
        if ctx.mode != "rule" and ctx.client:
            proc = process_player_action(
                TurnContext(
                    state=ctx.state,
                    action="combat_start",
                    turn=ctx.turn,
                    mode=ctx.mode,
                    manager=ctx.manager,
                    rules=ctx.rules,
                    client=ctx.client,
                )
            )
            lines.extend(proc["lines"])
        ctx.manager.save(ctx.state)
        return TurnResult(
            turn=ctx.turn,
            day=ctx.state["world"]["day"],
            time=time_label,
            mode=ctx.mode,
            lines=lines,
            moment_kind=moment_kind,
            time_steps=time_steps,
        )

    proc = process_player_action(ctx)
    lines.extend(proc["lines"])

    from utils.world_systems import tick_world_systems

    world_lines = tick_world_systems(
        ctx.state,
        base_dir=loader.base_dir,
        turn=ctx.turn,
        rng=ctx.rules.rng if hasattr(ctx.rules, "rng") else None,
    )
    lines.extend(world_lines)
    ctx.manager.save(ctx.state)
    return TurnResult(
        turn=ctx.turn,
        day=ctx.state["world"]["day"],
        time=time_label,
        mode=ctx.mode,
        lines=lines,
        decision=proc.get("decision"),
        moment_kind=moment_kind,
        time_steps=time_steps,
    )
