"""Ecology skill buffs — sovereign_buff application and tick."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.ecology_objects import skill_definition


def apply_buff_from_skill(
    agent: dict[str, Any],
    skill_id: str,
    sdef: dict[str, Any] | None = None,
    *,
    base_dir: str | Path,
) -> None:
    sd = sdef or skill_definition(skill_id, base_dir=base_dir)
    effects = dict(sd.get("effects", {}))
    duration = int(effects.get("duration_beats", sd.get("duration_beats", 8)))
    agent.setdefault("active_buffs", {})[skill_id] = {
        "skill_id": skill_id,
        "label": sd.get("label", skill_id),
        "effects": effects,
        "beats_remaining": duration,
    }


def is_buff_skill(sdef: dict[str, Any]) -> bool:
    return sdef.get("combat_pipeline") == "sovereign_buff" or "sovereign_buff" in sdef.get(
        "tags", []
    )


def tick_agent_buffs(agent: dict[str, Any], *, base_dir: str | Path) -> list[str]:
    lines: list[str] = []
    buffs = agent.get("active_buffs")
    if not buffs:
        return lines
    label = agent.get("label") or agent.get("archetype_id", "agent")
    from utils.combat_precision import from_milli, load_combat_precision_config

    cfg = load_combat_precision_config(base_dir)
    for sk_id in list(buffs.keys()):
        block = buffs[sk_id]
        effects = block.get("effects", {})
        regen_milli = int(effects.get("regen_per_sec_milli", 0))
        if regen_milli > 0:
            regen = max(1, int(round(from_milli(regen_milli, cfg=cfg))))
            mhp = int(agent.get("max_hp", agent.get("hp", 1)))
            agent["hp"] = min(mhp, int(agent.get("hp", 0)) + regen)
        block["beats_remaining"] = int(block.get("beats_remaining", 0)) - 1
        if block["beats_remaining"] <= 0:
            del buffs[sk_id]
            lines.append(f"[버프] {label} — {block.get('label', sk_id)} 종료")
    if not buffs:
        agent.pop("active_buffs", None)
    return lines


def apply_damage_with_buffs(
    target: dict[str, Any],
    raw_damage: int,
    *,
    base_dir: str | Path,
) -> int:
    if raw_damage <= 0:
        return 0
    buffs = target.get("active_buffs") or {}
    dr_milli = 0
    crisis_ratio: float | None = None
    for block in buffs.values():
        effects = block.get("effects", {})
        dr_milli = max(dr_milli, int(effects.get("damage_reduction_milli", 0)))
        if "crisis_hp_ratio" in effects:
            crisis_ratio = float(effects["crisis_hp_ratio"])

    from utils.combat_precision import fixed_scale, load_combat_precision_config

    cfg = load_combat_precision_config(base_dir)
    scale = fixed_scale(cfg)
    dmg = raw_damage
    if dr_milli > 0:
        dmg = int(dmg * (1.0 - min(1.0, dr_milli / scale)))

    mhp = max(1, int(target.get("max_hp", 1)))
    hp = int(target.get("hp", mhp))
    if crisis_ratio is not None and hp / mhp <= crisis_ratio and hp - dmg < 1:
        dmg = max(0, hp - 1)
    return max(0, dmg)
