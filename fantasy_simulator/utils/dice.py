"""Dice rolling helpers (stdlib only)."""

from __future__ import annotations

import random
from typing import Optional


def roll(sides: int = 20, count: int = 1, modifier: int = 0, rng: Optional[random.Random] = None) -> int:
    """Roll `count` dice with `sides` faces and apply modifier."""
    r = rng or random
    total = sum(r.randint(1, sides) for _ in range(count))
    return total + modifier


def roll_d20(modifier: int = 0, rng: Optional[random.Random] = None) -> tuple[int, int]:
    """Return (natural_roll, total_with_modifier)."""
    r = rng or random
    natural = r.randint(1, 20)
    return natural, natural + modifier
