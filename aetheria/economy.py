"""A living economy: merchants, stock and a market whose prices breathe.

Each tradeable item has a *market index* that drifts over time and reacts to world
events (a war drives up weapon prices; a good harvest lowers food).  Merchants buy
below and sell above the market price, modulated by the player's reputation and
charisma.  Gold is tracked in copper; helpers format it as gold/silver/copper.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .faction import FactionRegistry, Standing
from .items import ItemRegistry, ItemTemplate
from .rng import GameRandom
from .stats import Attribute


def format_coins(copper: int) -> str:
    gold, rem = divmod(max(0, copper), 100 * 100)
    silver, copper_rem = divmod(rem, 100)
    parts = []
    if gold:
        parts.append(f"{gold}g")
    if silver:
        parts.append(f"{silver}s")
    parts.append(f"{copper_rem}c")
    return " ".join(parts)


class Market:
    """Tracks a per-item price index that fluctuates with time and events."""

    def __init__(self, rng: GameRandom) -> None:
        self.rng = rng
        self.index: dict[str, float] = {}        # item_id -> multiplier around 1.0
        self.category_pressure: dict[str, float] = {}  # tag -> extra multiplier

    def _idx(self, item_id: str) -> float:
        return self.index.get(item_id, 1.0)

    def price_of(self, template: ItemTemplate) -> int:
        mult = self._idx(template.id)
        for tag in template.tags:
            mult *= self.category_pressure.get(tag, 1.0)
        return max(1, int(template.value * mult))

    def drift(self) -> None:
        """Gently pull each index back toward 1.0 with a little random walk."""
        for item_id in list(self.index):
            current = self.index[item_id]
            current += self.rng.gauss(0, 0.015)
            current += (1.0 - current) * 0.05          # mean reversion
            self.index[item_id] = max(0.5, min(2.5, current))
        for tag in list(self.category_pressure):
            cur = self.category_pressure[tag]
            cur += (1.0 - cur) * 0.08
            self.category_pressure[tag] = max(0.6, min(2.2, cur))
            if abs(cur - 1.0) < 0.01:
                del self.category_pressure[tag]

    def shock(self, item_id: str, multiplier: float) -> None:
        self.index[item_id] = max(0.5, min(2.5, self._idx(item_id) * multiplier))

    def pressure_category(self, tag: str, multiplier: float) -> None:
        cur = self.category_pressure.get(tag, 1.0)
        self.category_pressure[tag] = max(0.6, min(2.2, cur * multiplier))

    def to_dict(self) -> dict:
        return {"index": dict(self.index), "category_pressure": dict(self.category_pressure)}

    @classmethod
    def from_dict(cls, data: dict, rng: GameRandom) -> "Market":
        m = cls(rng)
        m.index = {k: float(v) for k, v in data.get("index", {}).items()}
        m.category_pressure = {k: float(v) for k, v in data.get("category_pressure", {}).items()}
        return m


@dataclass
class TradeQuote:
    item: ItemTemplate
    buy_price: int    # what the player pays to buy
    sell_price: int   # what the player receives when selling


class TradeSession:
    """Computes buy/sell quotes between a merchant NPC and the player."""

    SELL_MARGIN = 0.45   # players receive 45% of market when selling

    def __init__(self, market: Market, factions: FactionRegistry, rng: GameRandom) -> None:
        self.market = market
        self.factions = factions
        self.rng = rng

    def _reputation_modifier(self, player, faction_id: str) -> float:
        if not faction_id:
            return 1.0
        standing = Standing.from_score(player.reputation_with(faction_id))
        return standing.price_modifier

    def _charisma_modifier(self, player) -> float:
        cha = player.attrs.modifier(Attribute.CHARISMA)
        return max(0.85, 1.0 - cha * 0.02)

    def quote(self, registry: ItemRegistry, item_id: str, player, npc) -> TradeQuote:
        template = registry.get(item_id)
        base = self.market.price_of(template)
        rep = self._reputation_modifier(player, getattr(npc, "faction", ""))
        cha = self._charisma_modifier(player)
        buy = max(1, int(base * rep * cha))
        sell = max(1, int(base * self.SELL_MARGIN * (2.0 - cha + 0.0)))
        sell = max(1, min(sell, buy - 1)) if buy > 1 else 1
        return TradeQuote(template, buy, sell)

    def buy(self, registry, item_id: str, player, npc, quantity: int = 1) -> tuple[bool, str]:
        quote = self.quote(registry, item_id, player, npc)
        total = quote.buy_price * quantity
        if player.gold < total:
            return False, f"You need {format_coins(total)} but only have {format_coins(player.gold)}."
        player.gold -= total
        player.inventory.add(item_id, quantity)
        # buying nudges the price up a touch
        self.market.shock(item_id, 1.0 + 0.01 * quantity)
        return True, f"Bought {quantity}x {quote.item.name} for {format_coins(total)}."

    def sell(self, registry, item_id: str, player, npc, quantity: int = 1) -> tuple[bool, str]:
        if not player.inventory.has(item_id, quantity):
            return False, "You don't have that many to sell."
        quote = self.quote(registry, item_id, player, npc)
        total = quote.sell_price * quantity
        player.inventory.remove(item_id, quantity)
        player.gold += total
        self.market.shock(item_id, 1.0 - 0.01 * quantity)
        return True, f"Sold {quantity}x {quote.item.name} for {format_coins(total)}."
