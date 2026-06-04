#!/usr/bin/env python3
"""Fantasy Simulator — turn orchestrator with LLM routing."""

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
from utils.llm_router import describe_routes, route_action, route_consistency_check  # noqa: E402
from utils.rule_engine import RuleEngine  # noqa: E402
from utils.state_loader import StateLoader, event_entries  # noqa: E402
from utils.state_manager import StateManager  # noqa: E402

Mode = Literal["rule", "llm", "hybrid"]


def run_rule_based(
    rules: RuleEngine,
    loader: StateLoader,
    state: dict[str, Any],
    action: str,
    turn: int,
) -> dict[str, Any]:
    """Existing deterministic rule engine — used in rule/hybrid modes."""
    if state.get("combat") or action == "combat":
        return rules.run_combat_round(turn)
    if action == "explore":
        return rules.run_exploration(turn)
    if action == "rest":
        return rules.run_rest(turn, loader)
    return {"summary": f"Unknown action: {action}", "event_log_append": []}


def process_turn(
    state: dict[str, Any],
    action: str,
    *,
    mode: Mode,
    turn: int,
    manager: StateManager,
    rules: RuleEngine,
    client: LLMClient | None,
    mechanical: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Core turn loop: route → call model(s) → apply results."""
    snapshot = manager.snapshot()
    routes = route_action(action, state, mode=mode, turn=turn, base_dir=manager.base_dir)

    outcome_lines: list[str] = list(describe_routes(routes))
    results: list[dict[str, Any]] = []
    narrative_hint = (mechanical or {}).get("summary", "")
    quick_event: dict[str, Any] | None = None
    rules_text: dict[str, str] | None = None

    for step in routes:
        model = step["model"]

        if model == "rule":
            mech = mechanical if mechanical is not None else run_rule_based(
                rules, manager.loader, state, action, turn
            )
            mechanical = mech
            result = {"model": "rule", "role": "rule_engine", "mechanical": mech, "parsed": None, "text": ""}
            manager.apply_result(state, result, turn=turn)
            narrative_hint = mech.get("summary", narrative_hint)
            if mode == "rule":
                outcome_lines.extend(mech.get("lines", []))
                if mech.get("summary") and not mech.get("lines"):
                    outcome_lines.append(mech["summary"])
            results.append(result)
            continue

        if client is None:
            continue

        metadata: dict[str, Any] = {
            "mechanical_result": mechanical or {},
            "mechanical_summary": narrative_hint,
            "narrative_hint": narrative_hint,
            "quick_event": quick_event,
        }
        if step["role"] == "mechanics" and rules_text is None:
            rules_text = {
                "combat": manager.loader.load_rule("combat"),
                "magic_system": manager.loader.load_rule("magic_system"),
            }

        result = client.call_model(
            model,
            step.get("prompt_file"),
            snapshot,
            action,
            role=step["role"],
            route=step,
            metadata=metadata,
            rules=rules_text,
        )
        results.append(result)
        manager.apply_result(state, result, turn=turn)

        if result.get("parsed"):
            parsed = result["parsed"]
            if step["role"] == "quick_event":
                quick_event = parsed
                narrative_hint = parsed.get("description", narrative_hint)
            elif step["role"] == "mechanics":
                narrative_hint = parsed.get("description", narrative_hint)
                outcome_lines.append(parsed.get("description", ""))
                outcome_lines.extend(parsed.get("consequences", []))
            elif step["role"] == "world_arbiter":
                score = parsed.get("consistency_score")
                hint = parsed.get("narrative_direction_suggestion", "")
                outcome_lines.append(f"[world_arbiter] Consistency {score}/10 — {hint}")

        if result.get("text") and step["role"] == "narrator":
            outcome_lines.append(result["text"])

        prov = result.get("provider", "?")
        retries = result.get("retries", 0)
        label = f"{step['role']} [{step['model']}/{prov}]"
        if retries:
            label += f" retries={retries}"
        outcome_lines.append(label)

    # Consistency check (Opus world_arbiter) every N turns
    if mode in ("llm", "hybrid") and client is not None:
        for step in route_consistency_check(turn, state, base_dir=manager.base_dir):
            result = client.call_model(
                step["model"],
                step.get("prompt_file"),
                snapshot,
                "consistency_check",
                role=step["role"],
                route=step,
            )
            manager.apply_result(state, result, turn=turn)
            if result.get("parsed"):
                p = result["parsed"]
                outcome_lines.append(
                    f"[world_arbiter] Consistency {p.get('consistency_score')}/10 — "
                    f"{p.get('narrative_direction_suggestion', '')}"
                )

    manager.save(state)
    return {"routes": routes, "results": results, "lines": outcome_lines}


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
            "=== Turn Orchestrator ===",
            "  engine: simulation_engine.py",
            "  entry:  process_turn() → route_action() → call_claude/codex/gpt",
            "",
            "=== utils ===",
            "  llm_router.py   — route_action(action, state)",
            "  llm_client.py   — call_claude / call_codex / call_gpt",
            "  state_manager.py — load/save/snapshot/apply_result",
            "",
            "=== Prompt files ===",
            "  narrator_claude.md  → claude (Opus 4.8 High)",
            "  mechanics_codex.md  → codex (Codex 5.3 High)",
            "  world_arbiter.md    → claude (consistency JSON)",
            "  quick_event_gpt.md  → gpt   (GPT-5.5 High)",
            "",
            "=== Sample route (llm explore) ===",
        ]
        sample = route_action("explore", self.state, mode="llm", base_dir=self.loader.base_dir)
        lines.extend(f"  {line}" for line in describe_routes(sample))
        lines.extend(["", "=== Hybrid explore ==="])
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
