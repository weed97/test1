"""에리어 간 파괴력 지배 — 작은 에리어는 큰 에리어에 눌림."""

from __future__ import annotations


def dominance_ratio(local_extent: float, foreign_extent: float) -> float:
    """local / foreign — 1.0이면 동급, 작을수록 지배당함."""
    if foreign_extent <= 1e-9:
        return 1.0
    return min(1.0, local_extent / foreign_extent)


def effective_imbued_power(
    imbued: float,
    local_extent: float,
    *,
    foreign_extent: float | None = None,
) -> float:
    """같은 에리어 안에서는 전량, 타 에리어 대비 시 규모 비율로 감쇄."""
    if imbued <= 0.0:
        return 0.0
    if foreign_extent is None or foreign_extent <= local_extent:
        return imbued
    ratio = dominance_ratio(local_extent, foreign_extent)
    return imbued * ratio


def is_dominated(local_extent: float, foreign_extent: float, *, threshold: float = 0.65) -> bool:
    return dominance_ratio(local_extent, foreign_extent) < threshold
