"""A scripted, non-interactive playthrough used to showcase and verify Aetheria.

Run with ``python -m aetheria --demo``.  It drives a Warrior through conversation,
quest acceptance, trade, crafting, the living-world simulation and a battle, using a
prompt-aware auto-responder so it needs no human input.
"""

from __future__ import annotations

from .content import build_world
from .game import Game
from .game.factory import create_player


class AutoResponder:
    """Feeds queued answers; falls back to sensible defaults per sub-prompt."""

    def __init__(self) -> None:
        self.queue: list[str] = []

    def __call__(self, prompt: str = "") -> str:
        if self.queue:
            return self.queue.pop(0)
        p = prompt.lower()
        if "battle" in p:
            return "attack"
        if "say" in p or "gift" in p:
            return ""
        if "trade" in p:
            return "done"
        if "accept" in p:
            return "n"
        return "quit"


def _scene(title: str) -> None:
    print("\n" + "#" * 66)
    print(f"# {title}")
    print("#" * 66)


def run_demo(seed=None) -> None:
    if seed is None:
        seed = "demo-aldermere"
    io = AutoResponder()
    world = build_world(seed)
    game = Game(world, read=io)
    game.title_screen()
    create_player(world, "Garrok", "warrior")
    print(f"(Created Garrok the Warrior; world seed: {world.seed})")

    _scene("1. Where we begin")
    game.dispatch("look")
    game.dispatch("status")

    _scene("2. Into the tavern to meet the innkeeper")
    game.dispatch("go tavern")
    game.dispatch("who")
    # talk to Bram: ask rumours (2), ask for work (4), accept (y), leave ("")
    io.queue = ["2", "4", "y", ""]
    game.dispatch("talk Bram")
    game.dispatch("journal")

    _scene("3. Clearing the cellar (combat)")
    game.dispatch("go cellar")
    rats = [world.spawn_monster("giant_rat") for _ in range(3)]
    for r in rats:
        r.template_id = "giant_rat"
    io.queue = []
    game.run_combat(rats)
    game.dispatch("journal")

    _scene("4. Trading at the smithy")
    game.dispatch("go up")
    game.dispatch("go out")
    game.dispatch("go smithy")
    # talk to Mira, open trade (5), buy a helm, leave shop, leave convo
    io.queue = ["5", "buy iron_helm", "done", ""]
    game.dispatch("talk Mira")
    game.dispatch("inventory")
    game.dispatch("equip iron helm")

    _scene("5. Crafting at the forge")
    game.dispatch("recipes")
    # give Garrok materials to smelt iron
    world.player.inventory.add("iron_ore", 4)
    world.player.inventory.add("coal", 2)
    game.dispatch("craft smelt_iron")
    game.dispatch("inventory")

    _scene("6. The living world turns (simulate ~2 days)")
    before = world.clock.short()
    game.pass_time(48)
    print(f"Time advanced {before} -> {world.clock.short()}")
    game.dispatch("news")
    game.dispatch("time")

    _scene("7. A glimpse of the populace going about their lives")
    for npc in list(world.npcs.values())[:10]:
        loc = world.map.locations.get(npc.current_location)
        where = loc.name if loc else "?"
        print(f"  {npc.name:<26} {npc.role:<11} mood={npc.mood.value:<9} "
              f"at {where:<22} disp={npc.disposition.value}")

    _scene("8. Save & reload")
    game.dispatch("save demo")
    game.dispatch("load demo")
    game.dispatch("status")

    print("\nDemo complete. Run 'python -m aetheria' to play interactively.")
