"""Entry point: ``python -m aetheria``.

Modes
-----
* (default)         start a new game with interactive character creation
* --name/--class    skip creation (e.g. ``--name Aria --class mage``)
* --load SLOT       load a saved game
* --seed SEED       set the world seed (int or text)
* --simulate DAYS   run the world simulation head-less and print the chronicle
* --demo            run a short scripted playthrough (used for verification)
"""

from __future__ import annotations

import argparse
import sys

from .content import build_world
from .game import Game
from .game.factory import create_player
from .simulation import Simulation
from . import persistence


def run_simulation(seed, days: int) -> None:
    world = build_world(seed)
    sim = Simulation(world)
    print(f"Simulating {days} day(s) in Aldermere (seed: {world.seed})...\n")
    sim.run(days, verbose=True)
    print("=== Chronicle ===")
    for line in world.chronicle:
        print("  " + line)
    print(f"\nFinal date: {world.clock.stamp()}")
    print("\n=== A glimpse of the populace ===")
    for npc in list(world.npcs.values())[:8]:
        loc = world.map.locations.get(npc.current_location)
        where = loc.name if loc else "?"
        print(f"  {npc.name} ({npc.role}) — {npc.mood.value}, at {where}, "
              f"knows {len(npc.known_rumors)} rumour(s)")


def run_demo(seed) -> None:
    from .demo import run_demo as _demo
    _demo(seed)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="aetheria",
                                     description="A medieval-fantasy MMORPG world simulator.")
    parser.add_argument("--seed", default=None, help="world seed (int or text)")
    parser.add_argument("--name", default=None, help="character name (skips creation)")
    parser.add_argument("--class", dest="char_class", default=None,
                        help="class id: warrior/mage/rogue/ranger/cleric/paladin")
    parser.add_argument("--load", default=None, help="load a save slot")
    parser.add_argument("--simulate", type=int, default=None,
                        help="run the world simulation for N days and exit")
    parser.add_argument("--demo", action="store_true", help="run a scripted demo playthrough")
    args = parser.parse_args(argv)

    seed = args.seed
    if seed is not None and seed.isdigit():
        seed = int(seed)

    if args.simulate is not None:
        run_simulation(seed, args.simulate)
        return 0

    if args.demo:
        run_demo(seed)
        return 0

    if args.load:
        world = persistence.load(
            persistence.autosave_path(
                __import__("os").path.join(
                    __import__("os").path.expanduser("~"), ".aetheria", "saves"),
                args.load),
            build_world)
        game = Game(world)
        game.title_screen()
        game.describe_location(full=True)
    else:
        world = build_world(seed)
        game = Game(world)
        game.title_screen()
        if args.name and args.char_class:
            game.start_new(args.name, args.char_class)
        else:
            game.start_new()

    game.loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
