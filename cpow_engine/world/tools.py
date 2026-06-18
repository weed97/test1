"""채굴 도구 — 곡괭이·드릴 티어."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ToolType(str, Enum):
    PICKAXE = "pickaxe"
    DRILL = "drill"


@dataclass(frozen=True)
class ToolDef:
    tool_type: ToolType
    mining_tier: int
    mining_power: float
    max_hardness: int
    label: str

    def to_dict(self) -> dict:
        return {
            "tool_type": self.tool_type.value,
            "mining_tier": self.mining_tier,
            "mining_power": self.mining_power,
            "max_hardness": self.max_hardness,
            "label": self.label,
        }


def resolve_tool(tool_type: str, mining_tier: int) -> ToolDef | None:
    try:
        kind = ToolType(tool_type.lower())
    except ValueError:
        return None
    tier = max(0, min(6, int(mining_tier)))
    if kind == ToolType.PICKAXE:
        power = 1.0 + tier * 0.12
        max_hard = 2 + tier
        labels = ("나무 곡괭이", "돌 곡괭이", "철 곡괭이", "강철 곡괭이", "미스릴 곡괭이")
        label = labels[min(tier, len(labels) - 1)]
        return ToolDef(kind, tier, power, max_hard, label)
    power = 1.2 + tier * 0.18
    max_hard = 3 + tier
    labels = (
        "기본 드릴", "철 드릴", "강화 드릴", "다이아 비트 드릴",
        "미스릴 드릴", "지열 드릴", "블랙미스릴 드릴",
    )
    label = labels[min(tier, len(labels) - 1)]
    return ToolDef(kind, tier, power, max_hard, label)


def tool_catalog_public() -> list[dict]:
    out: list[dict] = []
    for kind in ToolType:
        for tier in range(7):
            tool = resolve_tool(kind.value, tier)
            if tool:
                out.append(tool.to_dict())
    return out
