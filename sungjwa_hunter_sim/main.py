#!/usr/bin/env python3
"""성좌 헌터 시뮬레이션 — 외부 시뮬레이터 CLI 진입점.

사용 예:
    python main.py
    python main.py --seed 42 --turns 8
    python main.py --hunter yoo_jonghyuk
    python main.py --list-hunters
    python main.py --list-monsters
    python main.py --interactive
    python main.py --query "[외부 업데이트] 질의: randomness_intensity=2.6, luck_factor=1.5"
    python main.py --json-out result.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import units  # noqa: E402
from src.external_update import ExternalUpdateHandler  # noqa: E402
from src.simulator import Simulator, _StopSimulation  # noqa: E402
from src.variables import VariableManager  # noqa: E402

DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "variables.json")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="성좌 헌터 시뮬레이션 외부 시뮬레이터",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--config", default=DEFAULT_CONFIG, help="변수 JSON 설정 파일 경로")
    p.add_argument("--seed", type=int, default=None, help="난수 시드 (재현용)")
    p.add_argument("--turns", type=int, default=None, help="최대 턴 수")
    p.add_argument("--delay", type=float, default=None, help="턴 사이 지연(초)")
    p.add_argument("--hunter", default=None, help="로스터에서 성좌 헌터 선택 (id)")
    p.add_argument("--interactive", action="store_true", help="턴 사이마다 외부 업데이트 질의 입력")
    p.add_argument("--query", default=None, help="단발성 [외부 업데이트] 질의 처리 후 종료")
    p.add_argument("--list-hunters", action="store_true", help="성좌 헌터 로스터 출력 후 종료")
    p.add_argument("--list-monsters", action="store_true", help="게이트 몬스터 유닛 출력 후 종료")
    p.add_argument("--no-persist", action="store_true", help="외부 업데이트를 JSON 파일에 저장하지 않음")
    p.add_argument("--json-out", default=None, help="종료 시 최종 상태를 JSON 파일로 저장")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        variables = VariableManager(args.config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[오류] {exc}", file=sys.stderr)
        return 2

    if args.list_hunters:
        print("성좌 헌터 로스터:")
        lines = units.roster_summary(variables)
        print("\n".join(lines) if lines else "  (등록된 로스터 없음)")
        return 0

    if args.list_monsters:
        print("게이트 몬스터 유닛 (예외 변수 포함):")
        lines = units.monster_summary(variables)
        print("\n".join(lines) if lines else "  (등록된 몬스터 없음)")
        return 0

    if args.query is not None:
        handler = ExternalUpdateHandler(variables, persist=not args.no_persist)
        print(handler.handle(args.query))
        return 0

    if args.hunter and args.hunter not in units.load_hunter_roster(variables):
        print(f"[오류] 알 수 없는 헌터 id: {args.hunter} (로스터: "
              f"{', '.join(units.load_hunter_roster(variables).keys())})", file=sys.stderr)
        return 2

    sim = Simulator(variables, seed=args.seed, hunter_id=args.hunter)
    sim.external.persist = not args.no_persist

    try:
        state = sim.run(max_turns=args.turns, delay=args.delay, interactive=args.interactive)
    except _StopSimulation:
        from src import ui
        print("\n" + ui.render_summary(sim.state))
        state = sim.state

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(state.to_dict(), fh, ensure_ascii=False, indent=2)
        print(f"\n[저장] 최종 상태를 '{args.json_out}'에 기록했습니다.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
