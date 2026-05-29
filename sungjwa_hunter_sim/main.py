#!/usr/bin/env python3
"""성좌 헌터 시뮬레이션 — 외부 시뮬레이터 CLI 진입점.

사용 예:
    # 기본 자동 진행 (config/variables.json 사용)
    python main.py

    # 시드 고정 + 턴 수 지정
    python main.py --seed 42 --turns 8

    # 턴 사이마다 [외부 업데이트] 질의를 입력받는 대화형 모드
    python main.py --interactive

    # 단발성 외부 업데이트 질의만 처리하고 종료
    python main.py --query "[외부 업데이트] 질의: randomness_intensity=2.6, luck_factor=1.5"

    # 종료 시 최종 상태를 JSON 으로 덤프
    python main.py --json-out result.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# 패키지/단독 실행 모두 지원
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    p.add_argument("--interactive", action="store_true", help="턴 사이마다 외부 업데이트 질의 입력")
    p.add_argument("--query", default=None, help="단발성 [외부 업데이트] 질의 처리 후 종료")
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

    # 단발성 외부 업데이트 질의 모드
    if args.query is not None:
        handler = ExternalUpdateHandler(variables, persist=not args.no_persist)
        print(handler.handle(args.query))
        return 0

    sim = Simulator(variables, seed=args.seed)
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
