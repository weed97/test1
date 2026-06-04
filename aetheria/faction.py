"""Factions and the player's reputation with them.

Reputation is a signed score per faction.  Helping a faction (completing its quests,
gifting its members, slaying its enemies) raises it; harming it lowers it.  The score
maps onto named *standings* that gate quests, prices and how guards react.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Standing(str, Enum):
    HATED = "Hated"
    HOSTILE = "Hostile"
    UNFRIENDLY = "Unfriendly"
    NEUTRAL = "Neutral"
    FRIENDLY = "Friendly"
    HONORED = "Honored"
    EXALTED = "Exalted"

    @classmethod
    def from_score(cls, score: int) -> "Standing":
        thresholds = [
            (-100, cls.HATED), (-50, cls.HOSTILE), (-15, cls.UNFRIENDLY),
            (25, cls.NEUTRAL), (75, cls.FRIENDLY), (150, cls.HONORED),
            (10**9, cls.EXALTED),
        ]
        for limit, standing in thresholds:
            if score < limit:
                return standing
        return cls.EXALTED

    @property
    def price_modifier(self) -> float:
        """Discount/markup merchants of this faction apply."""
        return {
            Standing.HATED: 1.6, Standing.HOSTILE: 1.4, Standing.UNFRIENDLY: 1.15,
            Standing.NEUTRAL: 1.0, Standing.FRIENDLY: 0.92, Standing.HONORED: 0.85,
            Standing.EXALTED: 0.75,
        }[self]


@dataclass
class Faction:
    id: str
    name: str
    description: str
    rivals: tuple[str, ...] = ()
    allies: tuple[str, ...] = ()
    home_region: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "rivals": list(self.rivals), "allies": list(self.allies),
            "home_region": self.home_region,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Faction":
        return cls(
            id=data["id"], name=data["name"], description=data["description"],
            rivals=tuple(data.get("rivals", [])), allies=tuple(data.get("allies", [])),
            home_region=data.get("home_region", ""),
        )


class FactionRegistry:
    def __init__(self) -> None:
        self._factions: dict[str, Faction] = {}

    def register(self, faction: Faction) -> Faction:
        self._factions[faction.id] = faction
        return faction

    def get(self, faction_id: str) -> Faction | None:
        return self._factions.get(faction_id)

    def all(self) -> list[Faction]:
        return list(self._factions.values())

    def apply_reputation(self, player, faction_id: str, delta: int) -> list[str]:
        """Adjust reputation, rippling to allied and rival factions."""
        messages: list[str] = []
        faction = self.get(faction_id)
        if not faction:
            player.adjust_reputation(faction_id, delta)
            return messages
        before = Standing.from_score(player.reputation_with(faction_id))
        player.adjust_reputation(faction_id, delta)
        after = Standing.from_score(player.reputation_with(faction_id))
        sign = "increased" if delta >= 0 else "decreased"
        messages.append(f"Reputation with {faction.name} {sign} by {abs(delta)}.")
        if before != after:
            messages.append(f"You are now {after.value} with {faction.name}.")
        for ally in faction.allies:
            player.adjust_reputation(ally, delta // 2)
        for rival in faction.rivals:
            player.adjust_reputation(rival, -delta // 2)
        return messages
