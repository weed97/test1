"""Command-line interface for the medieval fantasy simulator."""

from __future__ import annotations

import argparse
from pathlib import Path

from fantasy_mmorpg.engine import DEFAULT_SAVE_PATH, GameEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Play a medieval fantasy text MMORPG simulator.")
    parser.add_argument("--name", default="Alden", help="Player character name for a new game.")
    parser.add_argument(
        "--class",
        dest="class_name",
        default="knight",
        choices=("knight", "ranger", "mage", "cleric", "rogue", "commoner"),
        help="Starting class archetype.",
    )
    parser.add_argument("--load", type=Path, help="Load a saved game JSON file.")
    parser.add_argument("--seed", type=int, help="Seed random encounters for reproducible play.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.load:
        engine = GameEngine.load(args.load)
        print(f"Loaded {args.load}.")
    elif DEFAULT_SAVE_PATH.exists():
        engine = GameEngine.load(DEFAULT_SAVE_PATH)
        print(f"Loaded autosave from {DEFAULT_SAVE_PATH}. Use --name for a fresh character after moving/deleting it.")
    else:
        engine = GameEngine(GameEngine.create_player(args.name, args.class_name), seed=args.seed)
        print(f"Created {engine.player.name}, level 1 {engine.player.class_name}.")

    print("Welcome to Eldermist. Type 'help' for commands, 'quit' to leave.")
    print(engine.look())
    while True:
        prompt = (
            f"[Day {engine.world.day} {engine.world.hour:02d}:00 | "
            f"{engine.player.location.replace('_', ' ')} | "
            f"HP {engine.player.hp}/{engine.max_hp_with_equipment()}] > "
        )
        try:
            command = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nSaving before exit...")
            print(engine.save(DEFAULT_SAVE_PATH))
            return
        if command.strip().lower() in {"quit", "exit"}:
            print(engine.save(DEFAULT_SAVE_PATH))
            print("May your road be kinder than your omens.")
            return
        print(engine.handle(command))


if __name__ == "__main__":
    main()
