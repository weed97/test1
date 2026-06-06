from __future__ import annotations

import argparse

from .commands import CommandProcessor, HELP_TEXT
from .engine import SimulatorEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fantasy-mmorpg",
        description="Medieval fantasy text MMORPG mega simulator.",
    )
    parser.add_argument("--name", default="Wanderer", help="Player character name.")
    parser.add_argument("--seed", type=int, default=1337, help="Random seed for deterministic runs.")
    return parser


def run_loop(engine: SimulatorEngine) -> None:
    processor = CommandProcessor(engine)
    print("=== Medieval Fantasy Text MMORPG Simulator ===")
    print("Type 'help' for commands, 'exit' to quit.")
    print(engine.status())
    print("-" * 72)
    while True:
        try:
            command = input("mmorp> ")
        except EOFError:
            print("\nSession ended.")
            break
        except KeyboardInterrupt:
            print("\nInterrupted. Type 'exit' to quit cleanly.")
            continue

        result = processor.handle(command)
        if result == "__EXIT__":
            print("Farewell, traveler.")
            break
        print(result)
        print("-" * 72)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    engine = SimulatorEngine(player_name=args.name, seed=args.seed)
    run_loop(engine)


if __name__ == "__main__":
    main()
