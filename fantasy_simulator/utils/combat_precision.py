"""Mill-precision combat math — 0.001 stats, 0.001% rates, integer authority."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

_FIXED_SCALE = 1000
_RATE_SCALE = 100000


def load_combat_precision_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "combat_precision.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_power_tiers_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "power_tiers.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def attacker_has_armor_pierce(attacker: dict[str, Any], *, cfg: dict[str, Any]) -> bool:
    if attacker.get("armor_pierce") or attacker.get("excalibur_bound"):
        return True
    tier = str(attacker.get("tier", ""))
    ap = cfg.get("armor_pierce", {})
    return tier in ap.get("enabled_tiers", ["demigod", "excalibur_bound"])


def defender_is_demigod(defender: dict[str, Any]) -> bool:
    return str(defender.get("tier", "")) == "demigod" or bool(defender.get("world_sovereign"))


def hp_cap_milli_for_tier(tier: str, *, tiers_cfg: dict[str, Any]) -> int:
    tiers = tiers_cfg.get("tiers", {})
    if tier == "demigod":
        return int(tiers.get("demigod", {}).get("hp_cap_milli", 1_000_000_000))
    if tier in ("apex_mortal", "apex"):
        return int(tiers.get("apex_mortal", {}).get("hp_cap_milli", 99_999_000))
    return int(tiers_cfg.get("balance_guards", {}).get("max_hp_milli", 999_000))


def compute_pierce_damage_milli(attacker: dict[str, Any], *, cfg: dict[str, Any]) -> int:
    """Armor-piercing component — bypasses mitigation; demigod / Excalibur only."""
    if not attacker_has_armor_pierce(attacker, cfg=cfg):
        return 0
    ap = cfg.get("armor_pierce", {})
    cap = int(ap.get("max_pierce_per_hit_milli", 9_999_000))
    raw = int(attacker.get("pierce_attack_milli", attacker.get("attack_milli", 0)))
    return min(cap, max(0, raw))


def cap_mitigated_vs_demigod(mitigated_milli: int, *, cfg: dict[str, Any]) -> int:
    """Non-pierce attackers chip at most 1.000 HP vs demigod per strike."""
    chip = int(cfg.get("armor_pierce", {}).get("apex_mortal_chip_vs_demigod_milli", 1000))
    return min(chip, max(0, mitigated_milli))


def fixed_scale(cfg: dict[str, Any] | None = None) -> int:
    return int((cfg or {}).get("fixed_scale", _FIXED_SCALE))


def rate_scale(cfg: dict[str, Any] | None = None) -> int:
    return int((cfg or {}).get("rate_scale", _RATE_SCALE))


def to_milli(value: float, *, cfg: dict[str, Any] | None = None) -> int:
    return int(round(float(value) * fixed_scale(cfg)))


def from_milli(value: int, *, cfg: dict[str, Any] | None = None) -> float:
    return int(value) / fixed_scale(cfg)


def to_rate_milli(percent: float, *, cfg: dict[str, Any] | None = None) -> int:
    return int(round(float(percent) * rate_scale(cfg) / 100.0))


def from_rate_milli(value: int, *, cfg: dict[str, Any] | None = None) -> float:
    return int(value) * 100.0 / rate_scale(cfg)


def damage_through_rate_milli(defense_milli: int, *, cfg: dict[str, Any], magical: bool = False) -> int:
    """Fraction of damage that passes defense; reduction capped at 99.999%."""
    mit = cfg.get("mitigation", {})
    k = int(mit.get("k_mag_defense_milli" if magical else "k_defense_milli", 8_500_000))
    d = max(0, int(defense_milli))
    rs = rate_scale(cfg)
    min_through = int(mit.get("min_through_rate_milli", 1))
    max_red = int(mit.get("max_reduction_rate_milli", 99_999))
    if d <= 0:
        return rs
    floor = int(mit.get("sovereign_defense_floor_milli", 0))
    if floor > 0 and d >= floor:
        return min_through
    red = (max_red * d) // (d + k)
    red = min(max_red, max(0, red))
    through = rs - red
    return max(min_through, min(rs, through))


def defense_reduction_rate_milli(defense_milli: int, *, cfg: dict[str, Any], magical: bool = False) -> int:
    """Reduction rate in rate_scale units (derived from through)."""
    rs = rate_scale(cfg)
    return rs - damage_through_rate_milli(defense_milli, cfg=cfg, magical=magical)


def apply_mitigation_milli(
    attack_milli: int,
    defense_milli: int,
    *,
    cfg: dict[str, Any],
    magical: bool = False,
) -> int:
    """Post-mitigation damage milli with 99.999% reduction cap; min 0.001% through."""
    a = max(0, int(attack_milli))
    cap_raw = int(cfg.get("raw_damage_soft_cap_milli", 100_000_000))
    a = min(a, cap_raw)
    through = damage_through_rate_milli(defense_milli, cfg=cfg, magical=magical)
    rs = rate_scale(cfg)
    after = (a * through) // rs
    hit_cap = int(cfg.get("hp_damage_per_hit_cap_milli", 10_000_000))
    return min(hit_cap, after)


def mitigation_multiplier(defense_milli: int, *, cfg: dict[str, Any]) -> int:
    """Damage mult after armor as milli (1000 = 1.0×), derived from apply_mitigation."""
    k = int(cfg.get("mitigation", {}).get("k_defense_milli", 8_500_000))
    d = max(0, int(defense_milli))
    denom = k + d
    if denom <= 0:
        return _FIXED_SCALE
    return (k * _FIXED_SCALE) // denom


def level_supremacy_multiplier(
    attacker: dict[str, Any],
    defender: dict[str, Any],
    *,
    cfg: dict[str, Any],
) -> int:
    """Milli multiplier from char / weapon / grade level deltas."""
    ls = cfg.get("level_supremacy", {})
    cw = int(ls.get("character_weight_milli", 500))
    ww = int(ls.get("weapon_mastery_weight_milli", 350))
    gw = int(ls.get("grade_weight_milli", 150))
    per = int(ls.get("per_level_delta_milli", 1000))

    a_char = int(attacker.get("character_level", 1))
    d_char = int(defender.get("character_level", 1))
    a_wpn = int(attacker.get("weapon_mastery_level", 1))
    d_wpn = int(defender.get("weapon_mastery_level", 1))
    a_gr = int(attacker.get("item_grade_index", 0))
    d_gr = int(defender.get("item_grade_index", 0))

    score = (a_char - d_char) * cw + (a_wpn - d_wpn) * ww + (a_gr - d_gr) * gw
    # mult_milli = 1000 + score * per / 1000
    return _FIXED_SCALE + (score * per) // _FIXED_SCALE


def compute_hit_rate_milli(
    attacker: dict[str, Any],
    defender: dict[str, Any],
    *,
    cfg: dict[str, Any],
) -> int:
    ev = cfg.get("evasion", {})
    base = int(ev.get("base_hit_rate", _RATE_SCALE))
    mn = int(ev.get("min_hit_rate", 5000))
    mx = int(ev.get("max_hit_rate", 99500))
    acc = int(attacker.get("accuracy_milli", 0))
    eva = int(defender.get("evasion_milli", 0))
    acc_bonus = int(acc * float(ev.get("accuracy_per_milli_attack", 0.012)))
    eva_pen = int(eva * float(ev.get("evasion_per_milli_agi", 0.018)))
    hit = base + acc_bonus - eva_pen
    return max(mn, min(mx, hit))


def compute_crit_rate_milli(attacker: dict[str, Any], *, cfg: dict[str, Any]) -> int:
    cr = cfg.get("critical", {})
    base = int(cr.get("base_rate", 5000))
    mx = int(cr.get("max_rate", 75000))
    bonus = int(attacker.get("crit_rate_milli", 0))
    return max(0, min(mx, base + bonus))


def resolve_strike_damage_milli(
    attacker: dict[str, Any],
    defender: dict[str, Any],
    *,
    cfg: dict[str, Any],
    rng: random.Random,
    force_hit: bool | None = None,
    force_crit: bool | None = None,
) -> dict[str, Any]:
    """Full pipeline; returns milli damage and audit trail for balance tuning."""
    hit_rate = compute_hit_rate_milli(attacker, defender, cfg=cfg)
    hit = force_hit if force_hit is not None else rng.randint(1, _RATE_SCALE) <= hit_rate
    if not hit:
        return {
            "hit": False,
            "crit": False,
            "damage_milli": 0,
            "hit_rate_milli": hit_rate,
            "audit": {},
        }

    raw = int(attacker.get("attack_milli", 0))
    after_level = (raw * level_supremacy_multiplier(attacker, defender, cfg=cfg)) // _FIXED_SCALE
    def_m = int(defender.get("defense_milli", 0))
    after_armor = apply_mitigation_milli(after_level, def_m, cfg=cfg)
    if defender_is_demigod(defender) and not attacker_has_armor_pierce(attacker, cfg=cfg):
        after_armor = cap_mitigated_vs_demigod(after_armor, cfg=cfg)
    mit = mitigation_multiplier(def_m, cfg=cfg)
    pierce = compute_pierce_damage_milli(attacker, cfg=cfg)

    crit_rate = compute_crit_rate_milli(attacker, cfg=cfg)
    crit = force_crit if force_crit is not None else rng.randint(1, _RATE_SCALE) <= crit_rate
    crit_mult = int(cfg.get("critical", {}).get("damage_multiplier_milli", 2000))
    mitigated_final = after_armor
    if crit and pierce <= 0:
        mitigated_final = (after_armor * crit_mult) // _FIXED_SCALE
    elif crit and pierce > 0:
        mitigated_final = (after_armor * crit_mult) // _FIXED_SCALE

    hit_cap = int(cfg.get("hp_damage_per_hit_cap_milli", 10_000_000))
    mitigated_final = min(hit_cap, mitigated_final)
    min_d = int(cfg.get("min_final_damage_milli", 1000))
    if pierce <= 0:
        mitigated_final = max(min_d, mitigated_final)
    final = min(hit_cap, mitigated_final + pierce)

    return {
        "hit": True,
        "crit": crit,
        "damage_milli": final,
        "damage": from_milli(final, cfg=cfg),
        "hit_rate_milli": hit_rate,
        "crit_rate_milli": crit_rate,
        "armor_pierce_milli": pierce,
        "audit": {
            "raw_attack_milli": int(attacker.get("attack_milli", 0)),
            "after_level_supremacy_milli": after_level,
            "mitigation_mult_milli": mit,
            "after_armor_milli": after_armor,
            "mitigated_final_milli": mitigated_final,
            "pierce_milli": pierce,
            "final_milli": final,
        },
    }


def format_milli_stat(value: int, *, cfg: dict[str, Any] | None = None) -> str:
    return f"{from_milli(value, cfg=cfg):.3f}"


def format_rate_milli(value: int, *, cfg: dict[str, Any] | None = None) -> str:
    return f"{from_rate_milli(value, cfg=cfg):.3f}%"
