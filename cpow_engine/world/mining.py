"""채굴 숙련·시도 — 도구·경도·바이옴."""

from __future__ import annotations

from dataclasses import dataclass, field

from cpow_engine.models import CreativeObject, PropertyDef
from cpow_engine.world.ores import ORE_CATALOG, OreDef, OreSource
from cpow_engine.world.tools import ToolDef, ToolType, resolve_tool


_MINING_TIER_THRESHOLDS: tuple[tuple[float, int], ...] = (
    (100.0, 2),
    (500.0, 3),
    (2000.0, 4),
    (8000.0, 5),
    (25000.0, 6),
)


@dataclass
class MiningProfile:
    user_id: str
    xp: float = 0.0
    tier: int = 1
    totals: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "xp": round(self.xp, 2),
            "tier": self.tier,
            "totals": dict(self.totals),
        }


def tier_from_xp(xp: float) -> int:
    tier = 1
    for threshold, value in _MINING_TIER_THRESHOLDS:
        if xp >= threshold:
            tier = value
    return tier


def apply_mining_xp(profile: MiningProfile, ore_id: str, amount: float) -> None:
    profile.totals[ore_id] = profile.totals.get(ore_id, 0.0) + amount
    profile.xp += amount * (1.0 + ORE_CATALOG[ore_id].tier * 0.5)
    profile.tier = tier_from_xp(profile.xp)


@dataclass
class MineAttemptResult:
    ok: bool
    reason: str = ""
    ore_id: str = ""
    amount: float = 0.0
    resource: dict | None = None
    mining: dict | None = None

    def to_dict(self) -> dict:
        out: dict = {
            "ok": self.ok,
            "reason": self.reason,
            "ore_id": self.ore_id,
            "amount": self.amount,
        }
        if self.resource:
            out["resource"] = self.resource
        if self.mining:
            out["mining"] = self.mining
        return out


def _yield_amount(
    ore: OreDef,
    tool: ToolDef,
    profile: MiningProfile,
    *,
    hazard_penalty: float = 0.0,
) -> float:
    tier_bonus = 1.0 + profile.tier * 0.05
    base = ore.base_yield * tool.mining_power * tier_bonus
    if tool.tool_type == ToolType.DRILL and ore.hardness >= 4:
        base *= 1.15
    if tool.tool_type == ToolType.PICKAXE and ore.hardness >= 5:
        base *= 0.05
    base *= max(0.2, 1.0 - hazard_penalty)
    return max(0.0, round(base, 3))


def validate_mine_tool(ore: OreDef, tool: ToolDef) -> tuple[bool, str]:
    if ore.hardness > tool.max_hardness:
        return False, "tool_too_weak"
    if ore.tier >= 4 and tool.tool_type == ToolType.PICKAXE:
        return False, "requires_drill"
    if ore.ore_id == "black_mithril_ore" and tool.mining_tier < 6:
        return False, "requires_black_mithril_drill"
    return True, "ok"


def attempt_mine(
    *,
    actor_id: str,
    ore: OreDef,
    tool: ToolDef,
    profile: MiningProfile,
    consumable: str = "",
    hazard_danger: int = 0,
) -> MineAttemptResult:
    if ore.source == OreSource.BOSS:
        return MineAttemptResult(False, reason="boss_drop_only")
    if ore.requires_consumable and consumable != ore.requires_consumable:
        return MineAttemptResult(False, reason="missing_consumable")
    ok, reason = validate_mine_tool(ore, tool)
    if not ok:
        return MineAttemptResult(False, reason=reason)
    penalty = 0.15 * max(0, hazard_danger - 1)
    amount = _yield_amount(ore, tool, profile, hazard_penalty=penalty)
    if amount <= 0.0:
        return MineAttemptResult(False, reason="no_yield")
    apply_mining_xp(profile, ore.ore_id, amount)
    resource = build_resource_object(actor_id, ore.ore_id, amount).to_dict()
    return MineAttemptResult(
        True,
        reason="mined",
        ore_id=ore.ore_id,
        amount=amount,
        resource=resource,
        mining=profile.to_dict(),
    )


def build_resource_object(actor_id: str, ore_id: str, amount: float) -> CreativeObject:
    ore = ORE_CATALOG[ore_id]
    return CreativeObject(
        creator_id=actor_id,
        label=ore.label,
        properties=[
            PropertyDef("material_type", 0.0, ore_id),
            PropertyDef("purpose", 0.0, "resource"),
            PropertyDef("stack_amount", amount, "units"),
            PropertyDef("material_tier", float(int(ore.tier)), "tier"),
            PropertyDef("source", 0.0, ore.source.value),
        ],
    )


def parse_tool_from_payload(payload: dict) -> ToolDef:
    tool_type = str(payload.get("tool_type", "pickaxe"))
    tier = int(payload.get("tool_tier", payload.get("mining_tier", 1)))
    tool = resolve_tool(tool_type, tier)
    if tool is None:
        return resolve_tool("pickaxe", 1)  # type: ignore[return-value]
    return tool
