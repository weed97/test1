"""Deterministic dice & checks — the mechanical referee shared by every subsystem.

Reuses the Aetheria engine's seedable RNG when the package is importable, otherwise
falls back to the standard library.  Keeping all randomness here means a world seed
fully reproduces a run, which is essential for debugging a large simulation.
"""

from __future__ import annotations

from typing import Sequence, TypeVar

T = TypeVar("T")

try:  # prefer the engine RNG for cross-system determinism
    from aetheria.rng import GameRandom as _Backend  # type: ignore
    _HAS_ENGINE = True
except Exception:  # pragma: no cover - fallback path
    import random as _random

    class _Backend:  # minimal shim with the same surface we use
        def __init__(self, seed=None):
            if isinstance(seed, str):
                seed = sum(ord(c) * (i + 1) for i, c in enumerate(seed))
            self.seed = seed
            self._r = _random.Random(seed)

        def randint(self, a, b):
            return self._r.randint(a, b)

        def uniform(self, a, b):
            return self._r.uniform(a, b)

        def chance(self, p):
            return self._r.random() < p

        def choice(self, seq):
            return self._r.choice(seq)

        def choices(self, seq, weights=None, k=1):
            return self._r.choices(seq, weights=weights, k=k)

        def dice(self, count, sides):
            return sum(self._r.randint(1, sides) for _ in range(count))

        def percent(self):
            return self._r.randint(1, 100)

    _HAS_ENGINE = False


class Dice:
    """Thin façade over the RNG backend with RPG-flavoured helpers."""

    def __init__(self, seed: int | str | None = None) -> None:
        self.backend = _Backend(seed)
        self.seed = self.backend.seed

    def roll(self, count: int, sides: int, modifier: int = 0) -> int:
        return self.backend.dice(count, sides) + modifier

    def d20(self, modifier: int = 0) -> int:
        return self.backend.randint(1, 20) + modifier

    def d100(self) -> int:
        return self.backend.percent()

    def chance(self, probability: float) -> bool:
        return self.backend.chance(probability)

    def randint(self, low: int, high: int) -> int:
        return self.backend.randint(low, high)

    def choice(self, population: Sequence[T]) -> T:
        return self.backend.choice(population)

    def choices(self, population: Sequence[T], weights: Sequence[float] | None = None,
                k: int = 1) -> list[T]:
        return self.backend.choices(population, weights=weights, k=k)

    def check(self, modifier: int, difficulty: int) -> tuple[bool, int]:
        """A d20 ability check: returns (success, total)."""
        total = self.d20(modifier)
        return total >= difficulty, total

    def opposed(self, mod_a: int, mod_b: int) -> bool:
        """Opposed d20 check; True if side A wins ties included."""
        return self.d20(mod_a) >= self.d20(mod_b)
