"""Deterministic, seedable randomness for reproducible simulations.

A single :class:`GameRandom` instance is threaded through the whole engine so that
a given world seed always produces the same sequence of events.  This makes bugs
reproducible and lets players share "world seeds".
"""

from __future__ import annotations

import random
from typing import Sequence, TypeVar

T = TypeVar("T")


class GameRandom:
    """Thin, well-documented wrapper around :class:`random.Random`."""

    def __init__(self, seed: int | str | None = None) -> None:
        if isinstance(seed, str):
            seed = self._hash_seed(seed)
        self.seed: int = seed if seed is not None else random.randint(0, 2**63 - 1)
        self._rng = random.Random(self.seed)

    @staticmethod
    def _hash_seed(text: str) -> int:
        value = 1469598103934665603
        for ch in text:
            value ^= ord(ch)
            value = (value * 1099511628211) & 0xFFFFFFFFFFFFFFFF
        return value

    # -- basic draws ---------------------------------------------------------
    def chance(self, probability: float) -> bool:
        """Return ``True`` with the given probability in [0, 1]."""
        return self._rng.random() < probability

    def randint(self, low: int, high: int) -> int:
        return self._rng.randint(low, high)

    def uniform(self, low: float, high: float) -> float:
        return self._rng.uniform(low, high)

    def choice(self, population: Sequence[T]) -> T:
        return self._rng.choice(population)

    def choices(self, population: Sequence[T], weights: Sequence[float] | None = None,
                k: int = 1) -> list[T]:
        return self._rng.choices(population, weights=weights, k=k)

    def sample(self, population: Sequence[T], k: int) -> list[T]:
        k = max(0, min(k, len(population)))
        return self._rng.sample(list(population), k)

    def shuffle(self, items: list[T]) -> list[T]:
        self._rng.shuffle(items)
        return items

    def gauss(self, mu: float, sigma: float) -> float:
        return self._rng.gauss(mu, sigma)

    def dice(self, count: int, sides: int) -> int:
        """Roll ``count`` dice of ``sides`` faces (e.g. ``dice(2, 6)`` == 2d6)."""
        return sum(self._rng.randint(1, sides) for _ in range(max(0, count)))

    def percent(self) -> int:
        """A d100 roll (1-100)."""
        return self._rng.randint(1, 100)

    # -- state for save/load -------------------------------------------------
    def getstate(self) -> object:
        return self._rng.getstate()

    def setstate(self, state: object) -> None:
        self._rng.setstate(state)
