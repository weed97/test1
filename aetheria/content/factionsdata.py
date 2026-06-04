"""The great powers of the realm of Aldermere."""

from __future__ import annotations

from ..faction import Faction
from ..state import World


def register_factions(world: World) -> None:
    reg = world.factions
    add = reg.register

    add(Faction("crown", "The Crown of Aldermere",
                "The royal house and its knights, sworn to law and order.",
                rivals=("redhand", "shadowhand"), allies=("dawn",),
                home_region="capital"))
    add(Faction("merchants", "The Merchant Coalition",
                "A wealthy guild that controls trade across the realm.",
                rivals=("redhand",), allies=("crown",), home_region="vale"))
    add(Faction("conclave", "The Arcane Conclave",
                "Keepers of magical lore who guard dangerous secrets.",
                rivals=(), allies=("crown",), home_region="capital"))
    add(Faction("dawn", "The Order of the Dawn",
                "A faith devoted to light, healing and the smiting of evil.",
                rivals=("redhand",), allies=("crown",), home_region="vale"))
    add(Faction("shadowhand", "The Shadow Hand",
                "A secretive thieves' guild that thrives in the cracks of society.",
                rivals=("crown",), allies=(), home_region="capital"))
    add(Faction("redhand", "The Redhand Brigands",
                "Cutthroats and raiders who prey on the roads and the weak.",
                rivals=("crown", "merchants", "dawn"), allies=(), home_region="wilds"))
    add(Faction("fenfolk", "The Fenfolk",
                "Reclusive marsh-dwellers and their inscrutable hedge-witch.",
                rivals=(), allies=(), home_region="marsh"))
