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


def apply_mitigation_milli(attack_milli: int, defense_milli: int, *, cfg: dict[str, Any]) -> int:
    """Post-mitigation damage milli: atk×K/(K+def) — avoids mult rounding loss."""
    k = int(cfg.get("mitigation", {}).get("k_defense_milli", 8_500_000))
    d = max(0, int(defense_milli))
    a = max(0, int(attack_milli))
    denom = k + d
    return (a * k) // denom if denom > 0 else a


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
    mit = mitigation_multiplier(def_m, cfg=cfg)

    crit_rate = compute_crit_rate_milli(attacker, cfg=cfg)
    crit = force_crit if force_crit is not None else rng.randint(1, _RATE_SCALE) <= crit_rate
    crit_mult = int(cfg.get("critical", {}).get("damage_multiplier_milli", 2000))
    final = after_armor
    if crit:
        final = (after_armor * crit_mult) // _FIXED_SCALE

    min_d = int(cfg.get("min_final_damage_milli", 1000))
    max_d = int(cfg.get("balance_guards", {}).get("max_damage_per_strike_milli", 500_000_000))
    final = max(min_d, min(max_d, final))

    return {
        "hit": True,
        "crit": crit,
        "damage_milli": final,
        "damage": from_milli(final, cfg=cfg),
        "hit_rate_milli": hit_rate,
        "crit_rate_milli": crit_rate,
        "audit": {
            "raw_attack_milli": int(attacker.get("attack_milli", 0)),
            "after_level_supremacy_milli": after_level,
            "mitigation_mult_milli": mit,
            "after_armor_milli": after_armor,
            "final_milli": final,
        },
    }


def format_milli_stat(value: int, *, cfg: dict[str, Any] | None = None) -> str:
    return f"{from_milli(value, cfg=cfg):.3f}"


def format_rate_milli(value: int, *, cfg: dict[str, Any] | None = None) -> str:
    return f"{from_rate_milli(value, cfg=cfg):.3f}%"
