"""CLI entry: python3 -m cpow_engine.bot_sim"""

from __future__ import annotations

import json

from cpow_engine.bot_sim import run_bot_simulation


def main() -> None:
    report = run_bot_simulation(steps=25)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
