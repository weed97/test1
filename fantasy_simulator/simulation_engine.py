#!/usr/bin/env python3
"""Fantasy Simulator — multi-model orchestrator for Cursor.

Player action branching (see docs/CURSOR_MULTI_MODEL.md):
  서사 필요       → Claude Opus 4.8  (prompts/narrator_claude.md)
  규칙 적용 필요   → Codex 5.3 High   (prompts/mechanics_codex.md, JSON only)
  빠른 아이디어    → GPT-5.5 High     (prompts/quick_event_gpt.md)
  둘 다 필요       → 순차: Codex → Opus (기본 파이프라인)
  일관성 검사      → Opus + world_arbiter.md (5턴마다)

Central state: world_state.json (auto-synced each turn from state/ shards).
"""

from __future__ import annotations

import argparse
import copy
import random
import sys
from pathlib import Path
from typing import Any, Literal, Optional

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from utils.llm_client import LLMClient  # noqa: E402
from utils.llm_router import (  # noqa: E402
    classify_action_needs,
    decide_model_and_prompt,
    describe_routes,
    route_consistency_check,
)
from utils.rule_engine import RuleEngine  # noqa: E402
from utils.state_loader import StateLoader, event_entries  # noqa: E402
from utils.state_manager import StateManager  # noqa: E402

Mode = Literal["rule", "llm", "hybrid"]

PROMPT_NARRATOR = "narrator_claude.md"
PROMPT_MECHANICS = "mechanics_codex.md"
PROMPT_WORLD_ARBITER = "world_arbiter.md"
PROMPT_QUICK_EVENT = "quick_event_gpt.md"


def run_existing_rule_logic(
    rules: RuleEngine,
    loader: StateLoader,
    state: dict[str, Any],
    action: str,
    turn: int,
) -> dict[str, Any]:
    """기존 rule-based 엔진 (rule / hybrid 1단계)."""
    if state.get("combat") or action == "combat":
        return rules.run_combat_round(turn)
    if action == "explore":
        return rules.run_exploration(turn)
    if action == "rest":
        return rules.run_rest(turn, loader)
    return {"summary": f"Unknown action: {action}", "event_log_append": []}


def apply_changes_to_state(
    manager: StateManager,
    state: dict[str, Any],
    result: dict[str, Any],
    *,
    turn: int,
) -> dict[str, Any]:
    """Apply rule/LLM result to world state."""
    manager.apply_result(state, result, turn=turn)
    return state


def call_claude_narrator(
    client: LLMClient,
    snapshot: dict[str, Any],
    action: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return client.call_claude(PROMPT_NARRATOR, snapshot, action, role="narrator", metadata=metadata)


def call_codex_mechanics(
    client: LLMClient,
    snapshot: dict[str, Any],
    action: str,
    *,
    rules: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return client.call_codex(
        PROMPT_MECHANICS, snapshot, action, role="mechanics", rules=rules, metadata=metadata
    )


def call_gpt_quick_event(
    client: LLMClient,
    snapshot: dict[str, Any],
    action: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return client.call_gpt(PROMPT_QUICK_EVENT, snapshot, action, role="quick_event", metadata=metadata)


def handle_player_action(
    state: dict[str, Any],
    action: str,
    *,
    mode: Mode,
    turn: int,
    manager: StateManager,
    rules: RuleEngine,
    client: LLMClient | None,
) -> dict[str, Any]:
    """Minimal routing: decide_model_and_prompt → single model or rule engine."""
    decision = decide_model_and_prompt(action, state, mode=mode, base_dir=manager.base_dir)
    snapshot = manager.snapshot()
    outcome_lines: list[str] = [
        f"routing: model={decision['model']} priority={decision.get('priority')} "
        f"prompt={decision.get('prompt_file')}",
    ]
    results: list[dict[str, Any]] = []
    rules_text: dict[str, str] | None = None

    # Hybrid: run rule engine first, then optional LLM step
    if mode == "hybrid":
        mechanical = run_existing_rule_logic(rules, manager.loader, state, action, turn)
        rule_result: dict[str, Any] = {
            "model": "rule",
            "role": "rule_engine",
            "mechanical": mechanical,
            "parsed": None,
            "text": "",
        }
        apply_changes_to_state(manager, state, rule_result, turn=turn)
        results.append(rule_result)
        outcome_lines.extend(mechanical.get("lines", []))
        if mechanical.get("summary") and not mechanical.get("lines"):
            outcome_lines.append(mechanical["summary"])

    if not decision["use_llm"] or client is None:
        if mode != "hybrid":
            mechanical = run_existing_rule_logic(rules, manager.loader, state, action, turn)
            rule_result = {
                "model": "rule",
                "role": "rule_engine",
                "mechanical": mechanical,
                "parsed": None,
                "text": "",
            }
            apply_changes_to_state(manager, state, rule_result, turn=turn)
            results.append(rule_result)
            outcome_lines.extend(mechanical.get("lines", []))
            if mechanical.get("summary") and not mechanical.get("lines"):
                outcome_lines.append(mechanical["summary"])
        manager.save(state)
        return {"decision": decision, "results": results, "lines": outcome_lines}

    # Multi-step pipeline (when config defines more than one LLM step)
    pipeline = decision.get("pipeline") or []
    llm_steps = [s for s in pipeline if s.get("model") != "rule"]
    if not llm_steps:
        llm_steps = [{"model": decision["model"], "role": decision.get("role"), "prompt_file": decision.get("prompt_file")}]

    narrative_hint = ""
    for step in llm_steps:
        metadata: dict[str, Any] = {"narrative_hint": narrative_hint}
        model = step.get("model") or decision["model"]
        prompt_file = step.get("prompt_file") or decision.get("prompt_file")

        if model == "claude":
            pf = prompt_file.replace("prompts/", "") if prompt_file else PROMPT_NARRATOR
            result = client.call_claude(pf, snapshot, action, role="narrator", metadata=metadata)
        elif model == "codex":
            if rules_text is None:
                rules_text = {
                    "combat": manager.loader.load_rule("combat"),
                    "magic_system": manager.loader.load_rule("magic_system"),
                }
            pf = prompt_file.replace("prompts/", "") if prompt_file else PROMPT_MECHANICS
            result = client.call_codex(pf, snapshot, action, role="mechanics", rules=rules_text, metadata=metadata)
        elif model == "gpt":
            pf = prompt_file.replace("prompts/", "") if prompt_file else PROMPT_QUICK_EVENT
            result = client.call_gpt(pf, snapshot, action, role="quick_event", metadata=metadata)
        else:
            mechanical = run_existing_rule_logic(rules, manager.loader, state, action, turn)
            result = {"model": "rule", "role": "rule_engine", "mechanical": mechanical, "parsed": None, "text": ""}

        apply_changes_to_state(manager, state, result, turn=turn)
        results.append(result)

        if result.get("parsed"):
            parsed = result["parsed"]
            narrative_hint = parsed.get("description", narrative_hint)
            if step.get("role") == "mechanics":
                outcome_lines.append(parsed.get("description", ""))
                outcome_lines.extend(parsed.get("consequences", []))

        if result.get("text") and step.get("role") == "narrator":
            outcome_lines.append(result["text"])

        outcome_lines.append(f"{step.get('role', model)} [{model}/{result.get('provider', '?')}]")

    # Consistency check every N turns
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
            apply_changes_to_state(manager, state, result, turn=turn)
            if result.get("parsed"):
                p = result["parsed"]
                outcome_lines.append(
                    f"[world_arbiter] score={p.get('consistency_score')} "
                    f"issues={len(p.get('issues_found', []))}"
                )

    manager.save(state)
    return {"decision": decision, "results": results, "lines": outcome_lines}


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
    """Delegates to handle_player_action() — keyword routing entry point."""
    return handle_player_action(
        state, action, mode=mode, turn=turn, manager=manager, rules=rules, client=client
    )


def process_turn(
    state: dict[str, Any],
    action: str,
    *,
    mode: Mode,
    turn: int,
    manager: StateManager,
    rules: RuleEngine,
    client: LLMClient | None,
    mechanical: dict[str, Any] | None = None,  # noqa: ARG001 — kept for API compat
) -> dict[str, Any]:
    """Thin wrapper — delegates to process_player_action()."""
    return process_player_action(
        state, action, mode=mode, turn=turn, manager=manager, rules=rules, client=client
    )


class SimulationEngine:
    """Turn-based fantasy world orchestrator."""

    def __init__(
        self,
        loader: StateLoader,
        *,
        seed: Optional[int] = None,
        mode: Mode = "rule",
    ) -> None:
        self.loader = loader
        self.manager = StateManager(loader.base_dir)
        self.rng = random.Random(seed)
        self.mode = mode
        self.state = loader.load_world_state()
        self.rules = RuleEngine(self.state, self.rng)
        self.turn = len(event_entries(self.state))
        self.client: LLMClient | None = None
        if mode in ("llm", "hybrid"):
            self.client = LLMClient(loader.base_dir)

    def start_combat(self, enemy_id: str) -> None:
        enemy = copy.deepcopy(self.loader.load_character(enemy_id))
        party = [copy.deepcopy(c) for c in self.loader.load_party(self.state)]
        self.rules.start_combat(enemy, party, self.turn)
        self.loader.append_event_log(
            self.state,
            {"turn": self.turn, "type": "combat_start", "summary": f"전투 시작: {enemy['name']}"},
        )

    def run_turn(self, action: str = "explore") -> dict[str, Any]:
        self.turn += 1
        time_label = self.rules.advance_time()
        outcome_lines: list[str] = []

        # Combat start narration-only turn
        if action == "combat" and not self.state.get("combat"):
            self.start_combat("malachar_voidweaver")
            outcome_lines.append("전투가 시작되었다.")
            if self.mode != "rule" and self.client:
                proc = process_turn(
                    self.state,
                    "combat_start",
                    mode=self.mode,
                    turn=self.turn,
                    manager=self.manager,
                    rules=self.rules,
                    client=self.client,
                )
                outcome_lines.extend(proc["lines"])
            self.manager.save(self.state)
            return self._turn_result(time_label, outcome_lines)

        proc = process_turn(
            self.state,
            action,
            mode=self.mode,
            turn=self.turn,
            manager=self.manager,
            rules=self.rules,
            client=self.client,
        )
        outcome_lines.extend(proc["lines"])
        self.state = self.manager.load()
        return self._turn_result(time_label, outcome_lines)

    def _turn_result(self, time_label: str, lines: list[str]) -> dict[str, Any]:
        return {
            "turn": self.turn,
            "time": time_label,
            "day": self.state["world"]["day"],
            "mode": self.mode,
            "lines": lines,
        }

    def status_report(self) -> str:
        world = self.state["world"]
        lines = [
            f"=== {world['name']} | Day {world['day']} ({world['time_of_day']}) ===",
            f"모드: {self.mode} | 저장: state/ (sharded)",
            self.manager.summary(self.state),
            "",
            "파티:",
        ]
        for cid in self.state.get("party", []):
            c = self.loader.load_character(cid)
            if self.state.get("combat") and cid in self.state["combat"]["allies"]:
                stats = self.state["combat"]["allies"][cid]["stats"]
            else:
                stats = c["stats"]
            lines.append(
                f"  - {c['name']}: HP {stats['hp']}/{stats['max_hp']} "
                f"MP {stats['mana']}/{stats['max_mana']}"
            )
        if self.state.get("combat"):
            lines.extend(["", "(전투 진행 중)"])
        recent = event_entries(self.state)
        if recent:
            lines.extend(["", "최근 이벤트:"])
            for ev in recent[-5:]:
                lines.append(f"  [{ev.get('type')}] {ev.get('summary')}")
        return "\n".join(lines)

    def show_routing(self) -> str:
        from utils.llm_router import _load_routing

        routing = _load_routing(self.loader.base_dir)
        models = routing.get("models", {})
        lines = [
            "=== Multi-Model Architecture (Cursor) ===",
            "  See docs/CURSOR_MULTI_MODEL.md",
            "",
            "=== Turn Orchestrator ===",
            "  engine: simulation_engine.py + Cursor Composer",
            "  hub:    world_state.json (auto-sync each turn)",
            "",
            "=== Role → Model ===",
            "  서사·캐릭터  → Claude Opus 4.8  (narrator_claude.md)",
            "  규칙·메카닉스 → Codex 5.3 High   (mechanics_codex.md, JSON)",
            "  빠른 아이디어 → GPT-5.5 High      (quick_event_gpt.md)",
            "  일관성 검사  → Claude Opus 4.8  (world_arbiter.md, every 5 turns)",
            "",
            "=== Keyword routing (decide_model_and_prompt) ===",
            "  attack/cast/combat → Codex 5.3 (mechanics_codex.md)",
            "  explore/talk/look  → Claude Opus (narrator_claude.md)",
            "  rest / unknown     → rule_based",
            "",
            "=== Action needs (current: explore) ===",
        ]
        needs = classify_action_needs("explore", self.state)
        for k, v in needs.items():
            lines.append(f"  {k}: {v}")
        lines.extend([
            "",
            "=== handle_player_action API ===",
            "  handle_player_action() → decide_model_and_prompt() → call_claude/codex or rule",
            "",
            "=== Minimal routing API ===",
            "  classify_action_needs / decide_model_and_prompt",
            "  call_claude_narrator / call_codex_mechanics / call_gpt_quick_event",
            "",
            "=== Keyword samples ===",
        ])
        for sample_action in ("attack goblin", "explore forest", "rest"):
            d = decide_model_and_prompt(sample_action, self.state, mode="llm", base_dir=self.loader.base_dir)
            lines.append(
                f"  '{sample_action}' → model={d['model']} use_llm={d['use_llm']} priority={d.get('priority')}"
            )
        lines.extend([
            "",
            "=== Config pipeline (explore, fallback) ===",
        ])
        from utils.llm_router import route_action

        sample = route_action("explore", self.state, mode="llm", base_dir=self.loader.base_dir)
        lines.extend(f"  {line}" for line in describe_routes(sample))
        lines.extend(["", "=== decide_model_and_prompt (llm explore) ==="])
        d = decide_model_and_prompt("explore", self.state, mode="llm", base_dir=self.loader.base_dir)
        lines.append(f"  use_llm={d['use_llm']} model={d['model']} prompt={d.get('prompt_file')}")
        lines.extend(["", "=== Hybrid explore pipeline ==="])
        sample_h = route_action("explore", self.state, mode="hybrid", base_dir=self.loader.base_dir)
        lines.extend(f"  {line}" for line in describe_routes(sample_h))
        interval = routing.get("consistency_check_interval", 5)
        lines.append(f"\nConsistency check: every {interval} turns")
        return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fantasy Simulator — orchestration engine")
    p.add_argument("--root", default=str(ROOT), help="fantasy_simulator 디렉터리 경로")
    p.add_argument("--turns", type=int, default=1, help="실행할 턴 수")
    p.add_argument("--seed", type=int, default=None, help="난수 시드")
    p.add_argument(
        "--mode",
        choices=["rule", "llm", "hybrid"],
        default="rule",
        help="rule=규칙만, llm=LLM, hybrid=규칙+LLM",
    )
    p.add_argument(
        "--action",
        choices=["explore", "rest", "combat"],
        default="explore",
        help="턴 행동",
    )
    p.add_argument("--status", action="store_true", help="현재 상태 출력")
    p.add_argument("--show-prompts", action="store_true", help="프롬프트 파일 목록")
    p.add_argument("--show-routing", action="store_true", help="LLM 라우팅 구조")
    p.add_argument("--export-legacy", action="store_true", help="world_state.json 내보내기")
    p.add_argument("--combat", metavar="ENEMY_ID", help="보스 전투")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    loader = StateLoader.from_package_root(args.root)
    manager = StateManager(args.root)

    if args.export_legacy:
        manager.export_legacy()
        print("Exported legacy world_state.json from state/ shards.")
        return 0

    engine = SimulationEngine(loader, seed=args.seed, mode=args.mode)

    if args.show_routing:
        print(engine.show_routing())
        return 0

    if args.show_prompts:
        client = LLMClient(args.root)
        for name in (
            "narrator_claude.md",
            "mechanics_codex.md",
            "world_arbiter.md",
            "quick_event_gpt.md",
        ):
            text = client.load_prompt(name)
            print(f"--- prompts/{name} ({len(text)} chars) ---")
            print(text[:400] + ("..." if len(text) > 400 else ""))
            print()
        return 0

    if args.status:
        print(engine.status_report())
        return 0

    action = "combat" if args.combat else args.action
    if args.combat:
        engine.start_combat(args.combat)
        manager.save(engine.state)

    for _ in range(args.turns):
        result = engine.run_turn(action=action)
        print(f"\n[Turn {result['turn']}] Day {result['day']} — {result['time']} ({result['mode']})")
        for line in result["lines"]:
            print(f"  {line}")
        if action == "combat" and not engine.state.get("combat"):
            action = "explore"

    print("\n" + engine.status_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
