"""AOI — 관심 영역 거리."""

from __future__ import annotations

import math


def chebyshev_distance(x1: float, z1: float, x2: float, z2: float) -> float:
    return max(abs(x1 - x2), abs(z1 - z2))


def in_aoi(
    observer_x: float,
    observer_z: float,
    target_x: float,
    target_z: float,
    radius_m: float,
) -> bool:
    if radius_m <= 0:
        return True
    dx = observer_x - target_x
    dz = observer_z - target_z
    return math.hypot(dx, dz) <= radius_m
