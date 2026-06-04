"""The opening pool of tavern rumours circulating through the realm."""

from __future__ import annotations

from ..state import World

OPENING_RUMORS = [
    "they say a dragon has woken atop the Frostpeaks after three hundred years",
    "the Redhand bandits grow bolder every week on the King's Road",
    "the dead don't rest easy in the Mirewater Fen, or so the fenfolk whisper",
    "the Conclave in Highcrown is buying up old books at any price",
    "an old shrine in the Thornwood has gone strange — bones, and a cold that bites",
    "Master Coyne would sell his own grandmother if the price was right",
    "the Crown will make a lord of whoever ends the realm's troubles",
    "moonpetal fetches a good coin from the temple healers",
    "miners struck something in the deep mine they wish they hadn't",
    "the eastern lords sharpen their swords while Aldermere looks the other way",
]


def register_rumors(world: World) -> None:
    world.rumor_pool = list(OPENING_RUMORS)
