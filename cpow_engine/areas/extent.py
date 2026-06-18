"""에리어 규모 — 파괴력 상한·내구도·저항에 영향."""

from __future__ import annotations

import math

from cpow_engine.models import CreativeObject


def object_spatial_span(obj: CreativeObject) -> float:
    """오브젝트가 차지하는 공간 기여도."""
    scale = obj.get_property("scale")
    scale_val = scale.value if scale else 1.0
    span = scale_val
    for axis in ("spatial_x", "spatial_y", "spatial_z"):
        prop = obj.get_property(axis)
        if prop is not None:
            span += abs(prop.value) * 0.001
    return max(0.1, span)


def compute_extent(
    objects: dict[str, CreativeObject],
    *,
    extent_bonus: float = 1.0,
    member_count: int = 1,
) -> float:
    """에리어 실효 규모 — 오브젝트 수·스케일·보너스(확장) 반영."""
    if not objects:
        return max(1.0, extent_bonus)

    scale_sum = sum(object_spatial_span(o) for o in objects.values())
    count_factor = math.log2(1 + len(objects))
    member_factor = math.sqrt(max(1, member_count))
    raw = scale_sum * 0.35 + count_factor * 2.5 + member_factor
    return max(1.0, raw * extent_bonus)


def area_imbue_cap(extent: float) -> float:
    """에리어 규모당 오브젝트에 부여 가능한 파괴력 상한."""
    return 8.0 + extent * 4.5


def area_durability_cap(extent: float) -> float:
    """확장된 에리어에서 오브젝트가 버틸 수 있는 내구도 상한."""
    return 12.0 + extent * 5.0


def personal_imbue_cap(destruction_gauge_max: float, destruction_gauge: float) -> float:
    """개인 파괴력이 약하면 큰 유닛에 파괴력을 못 실음."""
    tier = destruction_gauge_max * 0.75 + destruction_gauge * 0.15
    return max(5.0, tier)


def max_imbue_amount(
    *,
    extent: float,
    destruction_gauge_max: float,
    destruction_gauge: float,
    already_imbued: float = 0.0,
) -> float:
    """개인·에리어 규모 중 더 낮은 쪽이 상한."""
    personal = personal_imbue_cap(destruction_gauge_max, destruction_gauge)
    regional = area_imbue_cap(extent)
    remaining = max(0.0, min(personal, regional) - already_imbued)
    return remaining


def max_object_durability_gate(
    *,
    extent: float,
    destruction_gauge_max: float,
    creation_data_score: float,
) -> float:
    """강한 파괴 유닛 — 본인 파괴력 또는 넓은 에리어 중 하나는 충족."""
    personal = destruction_gauge_max * 0.55 + max(0.0, creation_data_score) * 0.08
    regional = area_durability_cap(extent)
    return max(personal, regional)


def expansion_cost(current_bonus: float) -> tuple[float, float]:
    """에리어 확장 비용 — 창조력·파괴력 동시 소비."""
    tier = max(1, int(current_bonus))
    creation = 18.0 + tier * 6.0
    destruction = 10.0 + tier * 4.0
    return creation, destruction
