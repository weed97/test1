#!/usr/bin/env python3
"""Fantasy Simulator — orchestration loop with rule / LLM / hybrid modes."""

from __future__ import annotations

import argparse
import copy
import random
import sys
from pathlib import Path
from typing import Any, Literal, Optional

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from utils.llm.pipeline import TurnPipeline  # noqa: E402
from utils.rule_engine import RuleEngine  # noqa: E402
from utils.state_loader import StateLoader, event_entries  # noqa: E402

Mode = Literal["rule", "llm", "hybrid"]


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
        self.rng = random.Random(seed)
        self.mode = mode
        self.state = loader.load_world_state()
        self.rules = RuleEngine(self.state, self.rng)
        self.turn = len(event_entries(self.state))
        self.pipeline: TurnPipeline | None = None
        if mode in ("llm", "hybrid"):
            self.pipeline = TurnPipeline.create(loader.base_dir, loader)

    def start_combat(self, enemy_id: str) -> None:
        enemy = copy.deepcopy(self.loader.load_character(enemy_id))
        party = [copy.deepcopy(c) for c in self.loader.load_party(self.state)]
        self.rules.start_combat(enemy, party, self.turn)
        self.loader.append_event_log(
            self.state,
            {
                "turn": self.turn,
                "type": "combat_start",
                "summary": f"전투 시작: {enemy['name']}",
            },
        )

    def run_turn(self, action: str = "explore") -> dict[str, Any]:
        self.turn += 1
        time_label = self.rules.advance_time()
        outcome_lines: list[str] = []
        mechanical: dict[str, Any] | None = None

        if action == "combat" and not self.state.get("combat"):
            self.start_combat("malachar_voidweaver")
            outcome_lines.append("전투가 시작되었다.")
            if self.mode != "rule" and self.pipeline:
                snap = self.loader.store.llm_context_snapshot()
                results = self.pipeline.run("combat_start", state_snapshot=snap)
                if narr := self.pipeline.narration_text():
                    outcome_lines.append(narr)

        elif self.state.get("combat") or action == "combat":
            if self.mode == "rule":
                mechanical = self.rules.run_combat_round(self.turn)
                outcome_lines.extend(mechanical.get("lines", []))
                for entry in mechanical.get("event_log_append", []):
                    self.loader.append_event_log(self.state, entry)
                if mechanical.get("character_updates"):
                    self.loader.apply_character_updates(self.state, mechanical["character_updates"])
            else:
                mechanical = self.rules.run_combat_round(self.turn)
                for entry in mechanical.get("event_log_append", []):
                    self.loader.append_event_log(self.state, entry)
                if mechanical.get("character_updates"):
                    self.loader.apply_character_updates(self.state, mechanical["character_updates"])
                if self.pipeline:
                    snap = self.loader.store.llm_context_snapshot()
                    self.pipeline.run(
                        "combat",
                        state_snapshot=snap,
                        mechanical_result=mechanical,
                    )
                    outcome_lines.extend(self.pipeline.structured_logs() or mechanical.get("lines", []))
                    if narr := self.pipeline.narration_text():
                        outcome_lines.append(narr)

        elif action == "explore":
            if self.mode == "rule":
                mechanical = self.rules.run_exploration(self.turn)
                outcome_lines.append(mechanical["summary"])
                for entry in mechanical.get("event_log_append", []):
                    self.loader.append_event_log(self.state, entry)
            elif self.mode == "hybrid":
                mechanical = self.rules.run_exploration(self.turn)
                if self.pipeline:
                    snap = self.loader.store.llm_context_snapshot()
                    for entry in mechanical.get("event_log_append", []):
                        self.loader.append_event_log(self.state, entry)
                    self.pipeline.run(
                        "explore",
                        state_snapshot=snap,
                        mechanical_result=mechanical,
                        roles=["narrator"],
                    )
                    if narr := self.pipeline.narration_text():
                        outcome_lines.append(narr)
                    else:
                        outcome_lines.append(mechanical["summary"])
            else:  # llm
                if self.pipeline:
                    snap = self.loader.store.llm_context_snapshot()
                    self.pipeline.run("explore", state_snapshot=snap)
                    if narr := self.pipeline.narration_text():
                        outcome_lines.append(narr)
                    for r in self.pipeline.results:
                        if r.parsed and r.role == "world_arbiter":
                            hint = r.parsed.get("narrative_hint", "")
                            if hint:
                                outcome_lines.append(hint)

        elif action == "rest":
            mechanical = None
            if self.mode in ("rule", "hybrid"):
                mechanical = self.rules.run_rest(self.turn, self.loader)
                for entry in mechanical.get("event_log_append", []):
                    self.loader.append_event_log(self.state, entry)
            if self.mode == "llm" and self.pipeline:
                snap = self.loader.store.llm_context_snapshot()
                self.pipeline.run("rest", state_snapshot=snap)
                if narr := self.pipeline.narration_text():
                    outcome_lines.append(narr)
            elif self.mode == "hybrid" and self.pipeline:
                snap = self.loader.store.llm_context_snapshot()
                self.pipeline.run(
                    "rest",
                    state_snapshot=snap,
                    mechanical_result=mechanical,
                    roles=["narrator"],
                )
                if narr := self.pipeline.narration_text():
                    outcome_lines.append(narr)
                elif mechanical:
                    outcome_lines.append(mechanical["summary"])
            elif mechanical:
                outcome_lines.append(mechanical["summary"])

        else:
            outcome_lines.append(f"알 수 없는 행동: {action}")

        self.loader.save_world_state(self.state)
        return {
            "turn": self.turn,
            "time": time_label,
            "day": self.state["world"]["day"],
            "mode": self.mode,
            "lines": outcome_lines,
        }

    def status_report(self) -> str:
        world = self.state["world"]
        lines = [
            f"=== {world['name']} | Day {world['day']} ({world['time_of_day']}) ===",
            f"모드: {self.mode} | 저장: state/ (sharded)",
            f"위치: {world['location']}",
            f"날씨: {world['weather']} | 긴장도: {world.get('tension', 0):.2f}",
            f"골드: {self.state.get('inventory', {}).get('party_gold', 0)}",
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
            lines.append("")
            lines.append("(전투 진행 중)")
        recent = event_entries(self.state)
        if recent:
            lines.append("")
            lines.append("최근 이벤트:")
            for ev in recent[-5:]:
                lines.append(f"  [{ev.get('type')}] {ev.get('summary')}")
        return "\n".join(lines)

    def show_routing(self) -> str:
        router = self.loader.prompt_router
        lines = ["=== LLM Routing ==="]
        for role in self.loader.list_prompts():
            model = router.model_for_role(role)
            schema = router.schema_name_for_role(role) or "-"
            lines.append(f"  {role}: model={model}, schema={schema}")
        lines.append("")
        lines.append("Pipelines:")
        for action, roles in router.routing.get("pipelines", {}).items():
            lines.append(f"  {action}: {' → '.join(roles)}")
        return "\n".join(lines)

    def get_prompt_bundle(self) -> dict[str, str]:
        roles = self.loader.list_prompts()
        return {role: self.loader.load_prompt(role) for role in roles}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fantasy Simulator — orchestration engine")
    p.add_argument("--root", default=str(ROOT), help="fantasy_simulator 디렉터리 경로")
    p.add_argument("--turns", type=int, default=1, help="실행할 턴 수")
    p.add_argument("--seed", type=int, default=None, help="난수 시드")
    p.add_argument(
        "--mode",
        choices=["rule", "llm", "hybrid"],
        default="rule",
        help="rule=규칙만, llm=LLM 파이프라인, hybrid=규칙+LLM",
    )
    p.add_argument(
        "--action",
        choices=["explore", "rest", "combat"],
        default="explore",
        help="턴 행동",
    )
    p.add_argument("--status", action="store_true", help="현재 상태 출력 후 종료")
    p.add_argument("--show-prompts", action="store_true", help="역할별 프롬프트 목록 출력")
    p.add_argument("--show-routing", action="store_true", help="LLM 라우팅 설정 출력")
    p.add_argument("--export-legacy", action="store_true", help="world_state.json 단일 파일로 내보내기")
    p.add_argument("--combat", metavar="ENEMY_ID", help="지정 적과 전투 시작 후 진행")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    loader = StateLoader.from_package_root(args.root)

    if args.export_legacy:
        loader.store.export_legacy()
        print(f"Exported legacy world_state.json from state/ shards.")
        return 0

    engine = SimulationEngine(loader, seed=args.seed, mode=args.mode)

    if args.show_routing:
        print(engine.show_routing())
        return 0

    if args.show_prompts:
        for role, text in engine.get_prompt_bundle().items():
            model = loader.prompt_router.model_for_role(role)
            print(f"--- {role} (model={model}, {len(text)} chars) ---")
            print(text[:500] + ("..." if len(text) > 500 else ""))
            print()
        return 0

    if args.status:
        print(engine.status_report())
        return 0

    action = "combat" if args.combat else args.action
    if args.combat:
        engine.start_combat(args.combat)
        loader.save_world_state(engine.state)

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
