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

from utils.content_loader import ContentLoader  # noqa: E402
from utils.event_engine import EventEngine  # noqa: E402
from utils.llm_router import (  # noqa: E402
    classify_action_needs,
    decide_model_and_prompt,
    describe_routes,
    route_consistency_check,
)
from utils.rule_engine import RuleEngine  # noqa: E402
from utils.state_loader import StateLoader, event_entries  # noqa: E402
from utils.state_manager import StateManager  # noqa: E402
from utils.turn_processor import process_player_action  # noqa: E402

Mode = Literal["rule", "llm", "hybrid"]

PROMPT_WORLD_ARBITER = "world_arbiter.md"

INTERACTIVE_HELP = """\
명령어:
  explore              마을/주변 탐험 (씨앗 이벤트 발생 가능)
  investigate well     우물 조사
  investigate forest   북쪽 숲 조사 (퀘스트 2단계)
  talk torren          NPC 대화 (토렌/릴리안/회색 망토/장로/리사)
  rest                 휴식 (HP/MP 회복)
  combat silver_stalker  보스 전투 (3단계 이후)
  quest                퀘스트 진행 상황
  status               현재 상태
  help / quit

팁: 밤/저녁에 explore하면 다른 이벤트가 뜹니다.
"""


def load_world_state(manager: StateManager) -> dict[str, Any]:
    """Load world state from sharded state/ (+ world_state.json hub)."""
    return manager.load()


def save_world_state(manager: StateManager, state: dict[str, Any]) -> None:
    """Persist state/ shards and sync world_state.json hub."""
    manager.save(state)


def resolve_enemy_id(query: str, loader: StateLoader) -> str:
    """Match partial enemy name to characters/*.json id."""
    q = query.strip().lower().replace("-", "_").replace(" ", "_")
    char_dir = loader.base_dir / "characters"
    available = sorted(p.stem for p in char_dir.glob("*.json"))
    if q in available:
        return q
    for cid in available:
        if q in cid or cid.startswith(q):
            return cid
    return q


def parse_player_input(raw: str, loader: StateLoader | None = None) -> dict[str, Any]:
    """Parse REPL input into a structured command."""
    text = raw.strip()
    if not text:
        return {"kind": "empty"}
    lower = text.lower()
    if lower in ("quit", "exit", "q"):
        return {"kind": "quit"}
    if lower in ("status", "stat", "s"):
        return {"kind": "status"}
    if lower in ("help", "h", "?"):
        return {"kind": "help"}
    if lower.startswith("combat"):
        parts = text.split(maxsplit=1)
        enemy_query = parts[1] if len(parts) > 1 else "malachar"
        enemy_id = resolve_enemy_id(enemy_query, loader) if loader else enemy_query
        return {"kind": "turn", "action": "combat", "enemy_id": enemy_id}
    return {"kind": "turn", "action": text}


def print_turn_result(result: dict[str, Any]) -> None:
    print(f"\n[Turn {result['turn']}] Day {result['day']} — {result['time']} ({result['mode']})")
    for line in result["lines"]:
        print(f"  {line}")


def run_interactive_loop(engine: SimulationEngine) -> int:
    """Interactive while-True REPL for Cursor terminal play."""
    print("=== Eldoria 시뮬레이터 시작 ===")
    print(f"모드: {engine.mode}")
    print("명령어: explore, rest, combat <적>, status, help, quit")
    print("자유 입력도 가능 (예: 'cast fireball', 'investigate ruins')")

    while True:
        try:
            raw = input("\n행동을 입력하세요: ")
        except (EOFError, KeyboardInterrupt):
            print("\n\n게임 종료. 상태 저장 중...")
            save_world_state(engine.manager, engine.state)
            return 0

        parsed = parse_player_input(raw, engine.loader)
        kind = parsed["kind"]

        if kind == "empty":
            continue
        if kind == "quit":
            save_world_state(engine.manager, engine.state)
            print("게임 종료. 상태 저장 완료.")
            return 0
        if kind == "status":
            print(engine.status_report())
            continue
        if kind == "help":
            print(INTERACTIVE_HELP)
            continue

        try:
            result = engine.run_turn(
                action=parsed["action"],
                enemy_id=parsed.get("enemy_id"),
            )
        except (KeyError, FileNotFoundError, ValueError) as exc:
            print(f"  오류: {exc}")
            continue

        print_turn_result(result)
        save_world_state(engine.manager, engine.state)

    return 0


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
        self.manager = StateManager(loader.base_dir, store=loader.store)
        self.content = ContentLoader(loader.base_dir)
        self.rng = random.Random(seed)
        self.mode = mode
        self.state = loader.load_world_state()
        self.event_engine = EventEngine(self.content, self.rng)
        self.rules = RuleEngine(self.state, self.rng, event_engine=self.event_engine)
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
        self.manager.save(self.state)

    def run_turn(self, action: str = "explore", *, enemy_id: str | None = None) -> dict[str, Any]:
        self.turn += 1
        time_label = self.rules.advance_time()
        outcome_lines: list[str] = []

        # Combat start (combat / combat <enemy_id>)
        is_combat_start = action.lower().strip().startswith("combat") or action == "combat"
        if is_combat_start and not self.state.get("combat"):
            if enemy_id is None:
                parts = action.split(maxsplit=1)
                enemy_id = resolve_enemy_id(
                    parts[1] if len(parts) > 1 else "malachar",
                    self.loader,
                )
            self.start_combat(enemy_id)
            outcome_lines.append(f"전투가 시작되었다. (적: {enemy_id})")
            if self.mode != "rule" and self.client:
                proc = process_player_action(
                    self.state,
                    "combat_start",
                    mode=self.mode,
                    turn=self.turn,
                    manager=self.manager,
                    rules=self.rules,
                    client=self.client,
                )
                outcome_lines.extend(proc["lines"])
            self.manager.refresh_state(self.state)
            return self._turn_result(time_label, outcome_lines)

        proc = process_player_action(
            self.state,
            action,
            mode=self.mode,
            turn=self.turn,
            manager=self.manager,
            rules=self.rules,
            client=self.client,
        )
        outcome_lines.extend(proc["lines"])
        self.manager.refresh_state(self.state)
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
        rep = self.state.get("flags", {}).get("reputation", {})
        if rep:
            lines.extend(["", "평판:"])
            for k, v in sorted(rep.items()):
                lines.append(f"  - {k}: {v}")
        if self.event_engine:
            lines.extend(["", f"퀘스트: {self.event_engine.show_quest_status(self.state)}"])
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
            "=== Turn flow ===",
            "  SimulationEngine.run_turn → utils.turn_processor.process_player_action",
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
            "=== process_player_action (utils/turn_processor.py) ===",
            "  decide_model_and_prompt → rule engine and/or LLM → save + refresh_state",
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
        if self.client:
            lines.extend(["", self.client.format_provider_status()])
        elif self.mode in ("llm", "hybrid"):
            lines.extend(["", LLMClient(self.loader.base_dir).format_provider_status()])
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
    p.add_argument("--show-providers", action="store_true", help="LLM API 키 / mock 상태")
    p.add_argument("--export-legacy", action="store_true", help="world_state.json 내보내기")
    p.add_argument("--combat", metavar="ENEMY_ID", help="보스 전투")
    p.add_argument(
        "--batch",
        action="store_true",
        help="비대화형 배치 모드 (--turns/--action 사용)",
    )
    p.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="대화형 CLI (기본값: 터미널 연결 시)",
    )
    return p


def _should_run_interactive(args: argparse.Namespace) -> bool:
    """Interactive REPL unless batch/info flags are set."""
    if args.batch or args.combat or args.status:
        return False
    if args.show_routing or args.show_prompts or args.export_legacy or args.show_providers:
        return False
    if args.interactive:
        return True
    import sys

    if not sys.stdin.isatty():
        return False
    if args.turns != 1 or args.action != "explore":
        return False
    return True


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

    if args.show_providers:
        print(LLMClient(args.root).format_provider_status())
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

    if _should_run_interactive(args):
        return run_interactive_loop(engine)

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
