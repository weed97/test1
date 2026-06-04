"""World events — the headlines that make the realm feel alive.

The simulation periodically draws an event from the :class:`EventDeck`.  Each event
ripples outward: it shocks the market, shifts moods, may spawn rumours that NPCs then
repeat, and is written into the world chronicle.  Events are intentionally flavourful
and lightweight so dozens can fire over a long playthrough without bookkeeping pain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class WorldEvent:
    id: str
    headline: str
    rumor: str
    weight: float = 1.0
    market_shocks: tuple[tuple[str, float], ...] = ()       # (item_id, multiplier)
    category_pressure: tuple[tuple[str, float], ...] = ()   # (tag, multiplier)
    mood_shift: int = 0                                     # applied to all NPCs
    season: str | None = None                              # restrict to a season


# A broad deck of fantasy headlines.  Designers can keep appending to this list.
DEFAULT_EVENTS: list[WorldEvent] = [
    WorldEvent("war_drums", "War drums sound on the eastern border.",
               "They say the eastern lords are massing troops for war.",
               weight=1.0, category_pressure=(("weapon", 1.3), ("armor", 1.25)),
               mood_shift=-4),
    WorldEvent("good_harvest", "A bountiful harvest fills the granaries.",
               "This year's harvest is the best in a generation.",
               weight=1.2, category_pressure=(("food", 0.7),), mood_shift=5,
               season="Autumn"),
    WorldEvent("plague_scare", "A wasting sickness is whispered of in the slums.",
               "Folk are falling ill near the docks — keep your distance.",
               weight=0.7, category_pressure=(("potion", 1.5),), mood_shift=-6),
    WorldEvent("bandit_surge", "Bandits grow bold on the trade roads.",
               "Merchants won't travel the north road without an armed escort now.",
               weight=1.0, category_pressure=(("weapon", 1.15),), mood_shift=-3),
    WorldEvent("royal_wedding", "A royal wedding is announced in the capital.",
               "The crown prince is to wed — there'll be feasting for a week!",
               weight=0.8, category_pressure=(("luxury", 1.4), ("food", 1.1)),
               mood_shift=8),
    WorldEvent("dragon_sighting", "A dragon was seen circling the northern peaks.",
               "A shepherd swears he saw a dragon over the mountains at dusk.",
               weight=0.5, mood_shift=-5),
    WorldEvent("gold_strike", "A rich vein of ore is struck in the hills.",
               "Miners hit a fat vein up in the hills — fortunes to be made!",
               weight=0.8, category_pressure=(("ore", 0.75), ("gem", 0.85)),
               mood_shift=4),
    WorldEvent("festival", "The town readies for the Lantern Festival.",
               "The Lantern Festival's coming — they'll light the whole square.",
               weight=1.0, category_pressure=(("luxury", 1.2),), mood_shift=7),
    WorldEvent("dark_omen", "An eclipse darkens the noon sky.",
               "The sun went dark at midday — surely an ill omen.",
               weight=0.5, mood_shift=-7),
    WorldEvent("hero_returns", "A famed adventurer returns laden with treasure.",
               "A real hero rode in yesterday, saddlebags heavy with gold.",
               weight=0.9, category_pressure=(("treasure", 0.9),), mood_shift=6),
    WorldEvent("hard_winter", "An early frost grips the land.",
               "The cold came early this year. Stock up while you can.",
               weight=1.0, category_pressure=(("food", 1.3),), mood_shift=-4,
               season="Winter"),
    WorldEvent("guild_feud", "Two guilds come to blows in the market.",
               "The smiths and the merchants are at each other's throats again.",
               weight=0.8, mood_shift=-2),
]


class EventDeck:
    def __init__(self, events: list[WorldEvent] | None = None) -> None:
        self.events = list(events if events is not None else DEFAULT_EVENTS)

    def draw(self, rng, season: str) -> WorldEvent | None:
        eligible = [e for e in self.events if e.season is None or e.season == season]
        if not eligible:
            return None
        weights = [e.weight for e in eligible]
        return rng.choices(eligible, weights=weights, k=1)[0]

    def apply(self, event: WorldEvent, world) -> list[str]:
        log = [f"[NEWS] {event.headline}"]
        for item_id, mult in event.market_shocks:
            world.market.shock(item_id, mult)
        for tag, mult in event.category_pressure:
            world.market.pressure_category(tag, mult)
        if event.mood_shift:
            for npc in world.npcs.values():
                npc.adjust_mood(event.mood_shift)
        if event.rumor and event.rumor not in world.rumor_pool:
            world.rumor_pool.append(event.rumor)
            if len(world.rumor_pool) > 24:
                world.rumor_pool.pop(0)
        world.chronicle.append(f"{world.clock.short()} — {event.headline}")
        return log
