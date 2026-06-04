#!/usr/bin/env python3
"""Fantasy Simulator CLI — thin entry point.

Architecture:
  GameSession.run_turn() → turn_processor.execute_turn() → process_player_action()
See docs/ARCHITECTURE.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from utils.cli import run_interactive_loop  # noqa: E402
from utils.debug_info import format_routing_report  # noqa: E402
from utils.game_session import GameSession, SimulationEngine  # noqa: E402
from utils.llm_client import LLMClient  # noqa: E402
from utils.state_loader import StateLoader  # noqa: E402
from utils.state_manager import StateManager  # noqa: E402

# Re-exports for tests / backward compatibility
from utils.cli import (  # noqa: E402
    INTERACTIVE_HELP,
    parse_player_input,
    resolve_enemy_id,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fantasy Simulator — Eldoria")
    p.add_argument("--root", default=str(ROOT), help="fantasy_simulator 디렉터리 경로")
    p.add_argument("--turns", type=int, default=1, help="실행할 턴 수")
    p.add_argument("--seed", type=int, default=None, help="난수 시드")
    p.add_argument("--mode", choices=["rule", "llm", "hybrid"], default="rule")
    p.add_argument("--action", choices=["explore", "rest", "combat"], default="explore")
    p.add_argument("--status", action="store_true", help="현재 상태 출력")
    p.add_argument("--show-prompts", action="store_true")
    p.add_argument("--show-routing", action="store_true")
    p.add_argument("--show-providers", action="store_true")
    p.add_argument("--export-legacy", action="store_true")
    p.add_argument("--combat", metavar="ENEMY_ID")
    p.add_argument("--batch", action="store_true", help="비대화형 배치 모드")
    p.add_argument("--interactive", "-i", action="store_true")
    return p


def _should_run_interactive(args: argparse.Namespace) -> bool:
    if args.batch or args.combat or args.status:
        return False
    if args.show_routing or args.show_prompts or args.export_legacy or args.show_providers:
        return False
    if args.interactive:
        return True
    if not sys.stdin.isatty():
        return False
    if args.turns != 1 or args.action != "explore":
        return False
    return True


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    manager = StateManager(args.root)

    if args.export_legacy:
        manager.export_legacy()
        print("Exported world_state.json from state/ shards.")
        return 0

    session = GameSession.from_root(args.root, mode=args.mode, seed=args.seed)

    if args.show_routing:
        print(format_routing_report(session.state, session.manager.base_dir, mode=args.mode))
        return 0

    if args.show_providers:
        print(LLMClient(args.root).format_provider_status())
        return 0

    if args.show_prompts:
        client = LLMClient(args.root)
        for name in ("narrator_claude.md", "mechanics_codex.md", "world_arbiter.md", "quick_event_gpt.md"):
            text = client.load_prompt(name)
            print(f"--- prompts/{name} ({len(text)} chars) ---")
            print(text[:400] + ("..." if len(text) > 400 else ""))
            print()
        return 0

    if args.status:
        print(session.status_report())
        return 0

    if _should_run_interactive(args):
        return run_interactive_loop(session)

    action = "combat" if args.combat else args.action
    if args.combat:
        session.start_combat(args.combat)

    for _ in range(args.turns):
        result = session.run_turn(action=action)
        print(f"\n[Turn {result['turn']}] Day {result['day']} — {result['time']} ({result['mode']})")
        for line in result["lines"]:
            print(f"  {line}")
        if action == "combat" and not session.state.get("combat"):
            action = "explore"

    print("\n" + session.status_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
