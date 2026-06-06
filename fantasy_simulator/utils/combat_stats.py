"""Combat stats — snapshots, damage scaling, world pierce elites."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from utils.combat_precision import (
    fixed_scale,
    from_milli,
    load_combat_precision_config,
    resolve_strike_damage_milli,
    to_milli,
)

_GRADE_ORDER = (
    "common",
    "high",
    "rare",
    "hero",
    "legend",
    "mythic",
    "demigod",
)


def _read_json(base_dir: str | Path, rel: str) -> dict[str, Any]:
    path = Path(base_dir) / rel
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=4)
def _config_bundle(base_dir: str) -> dict[str, Any]:
    root = str(Path(base_dir).resolve())
    return {
        "precision": load_combat_precision_config(root),
        "stats": _read_json(root, "config/combat_stats.json"),
        "scaling": _read_json(root, "config/damage_scaling.json"),
        "elites": _read_json(root, "config/world_apex_elites.json"),
        "tiers": _read_json(root, "config/power_tiers.json"),
        "equipment": _read_json(root, "config/equipment_templates.json"),
        "jobs": _read_json(root, "config/job_stat_routes.json"),
        "combatants": _read_json(root, "config/combatants.json"),
        "coalition": _read_json(root, "config/arthur_coalition.json"),
    }


def load_combat_bundle(base_dir: str | Path) -> dict[str, Any]:
    return _config_bundle(str(Path(base_dir).resolve()))


def grade_index(grade: str) -> int:
    g = grade.lower()
    return _GRADE_ORDER.index(g) if g in _GRADE_ORDER else 0


def grade_base_damage(grade: str, *, bundle: dict[str, Any]) -> float:
    return float(bundle["scaling"]["weapon_grade_base_damage"].get(grade.lower(), 1))


def weapon_attack_base(wpn: dict[str, Any], grade: str, *, bundle: dict[str, Any]) -> float:
    if wpn.get("attack") is not None:
        return float(wpn["attack"])
    return grade_base_damage(grade, bundle=bundle)


def weapon_is_mythic_3t(wpn: dict[str, Any]) -> bool:
    return str(wpn.get("mythic_tier", "")).upper() == "3T"


def elite_pierce_dps(rank: int, *, bundle: dict[str, Any]) -> float:
    """방무 정예 DPS — 2위 1000, 순위당 -5%."""
    pe = bundle["elites"]["pierce_elite"]
    base = float(pe["base_pierce_dps"])
    fall = float(pe["dps_falloff_percent_per_rank_below_2"]) / 100.0
    if rank <= 2:
        return base
    return base * ((1.0 - fall) ** (rank - 2))


def elite_coalition_pierce_dps(*, bundle: dict[str, Any]) -> dict[str, Any]:
    """2~11위 전원 합산 방무 DPS."""
    per_rank = {str(r): elite_pierce_dps(r, bundle=bundle) for r in range(2, 12)}
    total = sum(per_rank.values())
    pe = bundle["elites"]["pierce_elite"]
    hp = int(bundle["coalition"].get("siege", {}).get("hp_milli", 1_000_000_000))
    regen = int(bundle["coalition"].get("siege", {}).get("regen_per_sec_milli", 160_000))
    net = max(0, int(total * 1000) - regen) // 1000
    secs = hp // max(1, int(total * 1000) - regen) if int(total * 1000) > regen else 0
    return {
        "per_rank_dps": per_rank,
        "combined_pierce_dps": round(total, 1),
        "target_combined_dps": pe.get("combined_dps_at_full_coalition", 5000),
        "realistic_range": [3000, 4000],
        "net_dps_after_regen": net,
        "seconds_to_kill_arthur": secs or int(pe.get("seconds_to_kill_arthur_1m_hp", 200)),
    }


def compute_skill_damage(
    snapshot: dict[str, Any],
    *,
    bundle: dict[str, Any],
    skill_power_percent: float = 700.0,
    skill_kind: str = "melee_phys_single",
    crit: bool = True,
) -> dict[str, Any]:
    """스탯·등급·스킬 계수 — 신화 10% 방무 분리."""
    sc = bundle["scaling"]
    grade = str(snapshot.get("weapon_grade", "mythic"))
    base = float(snapshot.get("weapon_attack_base", grade_base_damage(grade, bundle=bundle)))
    range_k = float(sc["range_coeff"]["melee" if "melee" in skill_kind else "ranged"])
    skill_k = float(sc["skill_coeff"].get(skill_kind, 1.0))
    prim = snapshot.get("primary") or {}
    str_mult = 1.0 + float(prim.get("str", 0)) * float(sc["stat_per_point"]["str_damage_percent_per_point"]) / 100.0
    int_mult = 1.0 + float(prim.get("int", 0)) * float(sc["stat_per_point"]["int_damage_percent_per_point"]) / 100.0
    stat_mult = str_mult if "magic" in skill_kind else str_mult
    if "magic" in skill_kind:
        stat_mult = int_mult
    if snapshot.get("suppress_character_level_scaling"):
        lv_mult = 1.0
    else:
        lv_mult = 1.0 + int(snapshot.get("character_level", 1)) * float(
            sc["stat_per_point"]["character_level_percent_per_level"]
        ) / 100.0
    power = skill_power_percent / 100.0
    crit_k = float(sc["critical_multiplier"]) if crit else 1.0
    total = base * range_k * skill_k * power * stat_mult * lv_mult * crit_k
    pierce_frac = float(sc.get("mythic_3t_pierce_fraction", 0.1))
    has_3t = bool(snapshot.get("mythic_3t_weapon"))
    rank = snapshot.get("world_apex_rank")
    pierce = total * pierce_frac if has_3t and rank and int(rank) >= 2 else 0.0
    return {
        "total_damage": round(total, 1),
        "pierce_damage": round(pierce, 1),
        "normal_damage": round(total - pierce, 1),
    }


def compute_primary_stats(
    job_id: str,
    *,
    character_level: int,
    job_level: int,
    jobs_cfg: dict[str, Any],
) -> dict[str, int]:
    job = jobs_cfg.get("jobs", {}).get(job_id, jobs_cfg.get("jobs", {}).get("wanderer", {}))
    stats: dict[str, int] = {}
    for key in jobs_cfg.get("stats", ["str", "agi", "vit", "int", "dex", "luck"]):
        jl = float(job.get("growth_per_job_level", {}).get(key, 0))
        cl = float(job.get("growth_per_character_level", {}).get(key, 0))
        stats[key] = max(1, int(jl * job_level + cl * character_level))
    return stats


def _weapon_template(equipment_cfg: dict[str, Any], weapon_id: str | None) -> dict[str, Any]:
    if not weapon_id:
        return {}
    return equipment_cfg.get("weapons", {}).get(weapon_id, {})


def _combatant_skill_ids(data: dict[str, Any], *, bundle: dict[str, Any]) -> list[str]:
    """Preset skills + weapon-granted skills (deduped, preset order first)."""
    seen: set[str] = set()
    ordered: list[str] = []
    for sk in data.get("skills") or []:
        sid = str(sk)
        if sid not in seen:
            seen.add(sid)
            ordered.append(sid)
    equip = data.get("equipment") or {}
    wpn = _weapon_template(bundle["equipment"], equip.get("weapon"))
    for sk in wpn.get("skills") or []:
        sid = str(sk)
        if sid not in seen:
            seen.add(sid)
            ordered.append(sid)
    return ordered


def _armor_template(equipment_cfg: dict[str, Any], armor_id: str | None) -> dict[str, Any]:
    if not armor_id:
        return {}
    return equipment_cfg.get("armor", {}).get(armor_id, {})


def hp_cap_milli_for(tier: str, *, bundle: dict[str, Any]) -> int:
    tiers = bundle["tiers"].get("tiers", {})
    if tier == "demigod":
        return int(tiers.get("demigod", {}).get("hp_cap_milli", 1_000_000_000))
    if tier == "apex_elite":
        return int(tiers.get("apex_elite", {}).get("hp_cap_milli", 500_000_000))
    if tier == "apex_mortal":
        return int(tiers.get("apex_mortal", {}).get("hp_cap_milli", 99_999_000))
    pools = bundle["stats"].get("hp_pools", {})
    return int(pools.get("default_mortal_cap_milli", 50_000_000))


def sovereign_melee_ttk_seconds(*, bundle: dict[str, Any]) -> float:
    """정예 HP ÷ 아서 방무 DPS — 근접 유지 시 생존 초."""
    elites = bundle["elites"]
    sa = bundle["scaling"]["sovereign_arthur"]
    hp = float(elites.get("elite_hp", sa.get("elite_hp_reference", 500_000)))
    dps = float(sa.get("pierce_dps", 100_000))
    return hp / max(1.0, dps)


def _apply_arthur_sovereign_fields(snap: dict[str, Any], *, bundle: dict[str, Any]) -> None:
    if not snap.get("world_sovereign"):
        return
    sa = bundle["scaling"]["sovereign_arthur"]
    prim = dict(snap.get("primary") or {})
    prim["str"] = int(sa.get("str_stat", 2000))
    snap["primary"] = prim
    aps = int(sa.get("attacks_per_sec", 10))
    dps = int(sa.get("pierce_dps", 100_000))
    per_hit = int(sa.get("pierce_per_hit", dps // max(1, aps)))
    max_basic = int(sa.get("max_damage_per_strike", per_hit))
    max_skill = int(sa.get("max_skill_damage_per_strike", 50_000))
    snap["pierce_dps_milli"] = dps * 1000
    snap["pierce_per_hit_milli"] = per_hit * 1000
    snap["max_damage_per_strike_milli"] = max_basic * 1000
    snap["max_skill_damage_per_strike_milli"] = max_skill * 1000
    snap["attack_milli"] = per_hit * 1000
    snap["attacks_per_sec_milli"] = aps * 1000
    snap["armor_pierce"] = True
    snap["pierce_fraction"] = float(sa.get("pierce_fraction", 1.0))
    snap["suppress_character_level_scaling"] = bool(sa.get("suppress_character_level_scaling", True))
    snap["sovereign_damage_capped"] = True
    snap["elite_melee_ttk_seconds"] = sovereign_melee_ttk_seconds(bundle=bundle)


def _apply_elite_pierce_fields(
    snap: dict[str, Any], *, bundle: dict[str, Any], wpn: dict[str, Any]
) -> None:
    rank = snap.get("world_apex_rank")
    if not rank or int(rank) < 2:
        return
    if not weapon_is_mythic_3t(wpn):
        snap["mythic_3t_weapon"] = False
        return
    snap["mythic_3t_weapon"] = True
    ri = int(rank)
    dps = elite_pierce_dps(ri, bundle=bundle)
    aps = int(bundle["elites"]["pierce_elite"].get("attacks_per_sec_rank_2", 5))
    snap["pierce_dps_milli"] = int(dps * 1000)
    snap["pierce_per_hit_milli"] = int(dps * 1000) // max(1, aps)
    snap["attacks_per_sec_milli"] = aps * 1000
    snap["tier"] = "apex_elite"
    snap["weapon_grade"] = "mythic"
    snap["mythic_partial_pierce"] = True
    elite_hp = bundle["elites"].get("elite_hp_milli")
    if elite_hp:
        snap["hp_milli"] = int(elite_hp)


def build_combatant_snapshot(
    *,
    base_dir: str | Path,
    preset_id: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle = load_combat_bundle(base_dir)
    cfg = bundle["precision"]
    data: dict[str, Any] = {}
    if preset_id:
        data.update(bundle["combatants"].get(preset_id, {}))
    if overrides:
        data.update(overrides)

    char_lv = int(data.get("character_level", 1))
    job_id = str(data.get("job_id", "wanderer"))
    job_lv = int(data.get("job_level", 1))
    wclass = str(data.get("weapon_class", "two_handed_sword"))
    wpn_lv = int(data.get("weapon_mastery_level", 1))
    tier = str(data.get("tier", "mortal"))
    equip = data.get("equipment") or {}

    prim = data.get("primary") or compute_primary_stats(
        job_id, character_level=char_lv, job_level=job_lv, jobs_cfg=bundle["jobs"]
    )
    if data.get("str_override"):
        prim = dict(prim)
        prim["str"] = int(data["str_override"])

    wpn = _weapon_template(bundle["equipment"], equip.get("weapon"))
    arm = _armor_template(bundle["equipment"], equip.get("armor"))
    w_grade = str(wpn.get("grade", data.get("weapon_grade", "common")))

    wpn_base = weapon_attack_base(wpn, w_grade, bundle=bundle)
    scale_dmg = compute_skill_damage(
        {
            "primary": prim,
            "character_level": char_lv,
            "weapon_grade": w_grade,
            "weapon_attack_base": wpn_base,
            "world_apex_rank": data.get("world_apex_rank"),
            "mythic_3t_weapon": weapon_is_mythic_3t(wpn),
            "suppress_character_level_scaling": bool(
                data.get("world_sovereign")
                and bundle["scaling"]["sovereign_arthur"].get("suppress_character_level_scaling")
            ),
        },
        bundle=bundle,
        skill_power_percent=float(data.get("skill_power_percent", 100)),
        skill_kind=str(data.get("skill_kind", "melee_phys_single")),
        crit=False,
    )
    attack_milli = to_milli(scale_dmg["total_damage"], cfg=cfg)
    attack_milli = min(attack_milli, int(cfg.get("raw_damage_soft_cap_milli", 100_000_000)))

    def_m = to_milli(float(arm.get("defense", prim.get("vit", 10) * 0.35)), cfg=cfg)
    if tier == "demigod":
        def_m = max(def_m, int(cfg.get("mitigation", {}).get("sovereign_defense_floor_milli", 100_000_000)))

    vit_hp = to_milli(prim.get("vit", 10) * 8.5 + char_lv * 2.2, cfg=cfg)
    hp_milli = min(hp_cap_milli_for(tier, bundle=bundle), max(vit_hp, 5_000))

    snap: dict[str, Any] = {
        "id": preset_id or data.get("id", "custom"),
        "label": data.get("label", preset_id or "combatant"),
        "job_id": job_id,
        "tier": tier,
        "character_level": char_lv,
        "weapon_mastery_level": wpn_lv,
        "item_grade_index": grade_index(w_grade),
        "weapon_grade": w_grade,
        "attack_milli": attack_milli,
        "defense_milli": def_m,
        "hp_milli": hp_milli,
        "primary": prim,
        "weapon_class": wclass,
        "armor_pierce": bool(data.get("armor_pierce") or data.get("excalibur_bound")),
        "excalibur_bound": bool(data.get("excalibur_bound")),
        "world_sovereign": bool(data.get("world_sovereign")),
        "world_apex_rank": data.get("world_apex_rank"),
    }
    if data.get("hp_override_milli"):
        snap["hp_milli"] = int(data["hp_override_milli"])
    elif tier == "demigod" and bundle["coalition"].get("world_sovereign", {}).get("hp_milli"):
        snap["hp_milli"] = int(bundle["coalition"]["world_sovereign"]["hp_milli"])
    skills = _combatant_skill_ids(data, bundle=bundle)
    if skills:
        snap["skills"] = skills
    _apply_arthur_sovereign_fields(snap, bundle=bundle)
    _apply_elite_pierce_fields(snap, bundle=bundle, wpn=wpn)
    return snap


def _ultimate_vital_dodge_pixels(target: dict[str, Any], ult_cfg: dict[str, Any]) -> int:
    """궁극기 시전 중 스킬 불능 — 마법사만 순수 바이탈로 최대 N px 회피."""
    dodge = ult_cfg.get("dodge", {})
    job = str(target.get("job_id", ""))
    if job not in dodge.get("eligible_job_ids", []):
        return 0
    return int(dodge.get("pure_vital_dodge_pixels", 10))


def _in_ultimate_blast(
    distance_pixels: int,
    *,
    radius_pixels: int,
    vital_dodge_pixels: int,
) -> bool:
    """시전 후 바깥으로 vital_dodge_px만큼 이동해도 반경 밖이 안 되면 적중."""
    return int(distance_pixels) + int(vital_dodge_pixels) <= int(radius_pixels)


def _sovereign_skill_multiplier(sdef: dict[str, Any]) -> float:
    mode = str(sdef.get("sovereign_strike_mode", "skill"))
    if mode == "basic":
        return 1.0
    power = float(sdef.get("power", 10))
    return max(1.0, power / 10.0)


def preview_arthur_skill_damage(
    attacker: dict[str, Any],
    target: dict[str, Any],
    skill_id: str,
    *,
    base_dir: str | Path,
    rng: Any,
) -> dict[str, Any]:
    """Single-target preview for Arthur sovereign skills (agent_mind / parallel_beat)."""
    from utils.ecology_objects import skill_definition

    sdef = skill_definition(skill_id, base_dir=base_dir)
    pipeline = str(sdef.get("combat_pipeline", ""))
    bundle = load_combat_bundle(base_dir)

    if pipeline == "sovereign_strike":
        mult = _sovereign_skill_multiplier(sdef)
        strike = _sovereign_strike_damage_milli(attacker, skill_multiplier=mult)
        return {
            "skill_id": skill_id,
            "pipeline": pipeline,
            "damage_milli": int(strike["damage_milli"]),
            "sovereign_capped": True,
        }

    if pipeline == "sovereign_aoe":
        ultimate = bool(sdef.get("aoe_ultimate", False))
        t = dict(target)
        t.setdefault("distance_pixels", 0)
        aoe = resolve_excalibur_aoe(attacker, [t], bundle=bundle, ultimate=ultimate)
        hit = aoe["results"][0] if aoe.get("results") else {}
        return {
            "skill_id": skill_id,
            "pipeline": pipeline,
            "ultimate": ultimate,
            "damage_milli": int(hit.get("damage_milli", 0)),
            "killed": bool(hit.get("killed", False)),
            "aoe": aoe,
        }

    if pipeline == "sovereign_buff":
        return {
            "skill_id": skill_id,
            "pipeline": pipeline,
            "damage_milli": 0,
            "buff": dict(sdef.get("effects", {})),
        }

    if pipeline == "world_edict":
        return {
            "skill_id": skill_id,
            "pipeline": pipeline,
            "damage_milli": 0,
            "wish_interval_years": int(sdef.get("wish_interval_years", 4)),
            "power_id": str(sdef.get("power_id", "sovereign_wish")),
            "config_ref": str(sdef.get("config_ref", "config/demigod_sovereign.json")),
        }

    mult = _sovereign_skill_multiplier(sdef)
    strike = _sovereign_strike_damage_milli(attacker, skill_multiplier=mult)
    return {
        "skill_id": skill_id,
        "pipeline": pipeline or "sovereign_strike",
        "damage_milli": int(strike["damage_milli"]),
    }


def resolve_arthur_skill(
    skill_id: str,
    attacker: dict[str, Any],
    targets: list[dict[str, Any]],
    *,
    base_dir: str | Path,
    rng: Any | None = None,
) -> dict[str, Any]:
    """Resolve one Arthur core skill through the sovereign combat pipeline."""
    from utils.ecology_objects import skill_definition

    sdef = skill_definition(skill_id, base_dir=base_dir)
    pipeline = str(sdef.get("combat_pipeline", ""))
    bundle = load_combat_bundle(base_dir)

    if pipeline == "sovereign_strike":
        mult = _sovereign_skill_multiplier(sdef)
        hits = int(sdef.get("hits_per_cast", 1))
        per_target: list[dict[str, Any]] = []
        for t in targets:
            strike = _sovereign_strike_damage_milli(attacker, skill_multiplier=mult)
            total = int(strike["damage_milli"]) * hits
            per_target.append(
                {
                    "target_id": t.get("id"),
                    "hits": hits,
                    "damage_milli": total,
                    "per_hit_milli": int(strike["damage_milli"]),
                    "sovereign_capped": True,
                }
            )
        return {
            "skill_id": skill_id,
            "label": sdef.get("label", skill_id),
            "pipeline": pipeline,
            "results": per_target,
        }

    if pipeline == "sovereign_aoe":
        ultimate = bool(sdef.get("aoe_ultimate", False))
        aoe = resolve_excalibur_aoe(attacker, targets, bundle=bundle, ultimate=ultimate)
        return {
            "skill_id": skill_id,
            "label": sdef.get("label", skill_id),
            "pipeline": pipeline,
            "aoe": aoe,
        }

    if pipeline == "sovereign_buff":
        return {
            "skill_id": skill_id,
            "label": sdef.get("label", skill_id),
            "pipeline": pipeline,
            "buff": dict(sdef.get("effects", {})),
            "duration_beats": int(sdef.get("effects", {}).get("duration_beats", 8)),
            "targets": [t.get("id") for t in targets],
        }

    if pipeline == "world_edict":
        demigod = _read_json(base_dir, "config/demigod_sovereign.json")
        return {
            "skill_id": skill_id,
            "label": sdef.get("label", skill_id),
            "pipeline": pipeline,
            "power_id": str(sdef.get("power_id", demigod.get("excalibur", {}).get("power_id", "sovereign_wish"))),
            "wish_interval_years": int(
                sdef.get("wish_interval_years", demigod.get("excalibur", {}).get("wish_interval_years", 4))
            ),
            "forbidden_edicts": list(demigod.get("forbidden_edicts", [])),
            "wish_edict_types": list(demigod.get("wish_edict_types", [])),
            "combat_damage": False,
        }

    mult = _sovereign_skill_multiplier(sdef)
    strike = _sovereign_strike_damage_milli(attacker, skill_multiplier=mult)
    return {
        "skill_id": skill_id,
        "label": sdef.get("label", skill_id),
        "pipeline": pipeline or "sovereign_strike",
        "results": [
            {
                "target_id": t.get("id"),
                "damage_milli": int(strike["damage_milli"]),
            }
            for t in targets
        ],
    }


def resolve_excalibur_aoe(
    attacker: dict[str, Any],
    targets: list[dict[str, Any]],
    *,
    bundle: dict[str, Any],
    ultimate: bool = False,
) -> dict[str, Any]:
    """아서 광역 — 일반(×0.5) vs 성검 궁극기(원샷·100px·마법사 10px 바이탈 회피)."""
    ult_cfg = bundle["scaling"]["excalibur_ultimate"]
    radius = int(ult_cfg.get("radius_pixels", 100))
    per_hit = int(attacker.get("pierce_per_hit_milli", 10_000_000))
    coeff = float(ult_cfg.get("aoe_coeff", 0.5))
    aoe_hit = int(per_hit * coeff)
    cluster_cfg = ult_cfg.get("cluster_wipe", {})
    cluster_max = int(cluster_cfg.get("clustered_max_distance_pixels", 50))
    coalition_n = int(cluster_cfg.get("full_coalition_count", 10))
    results: list[dict[str, Any]] = []
    kills = 0
    in_radius = 0
    for t in targets:
        hp = int(t.get("hp_milli", 0))
        dist = int(t.get("distance_pixels", 0))
        dodge_px = _ultimate_vital_dodge_pixels(t, ult_cfg) if ultimate else 0
        blasted = _in_ultimate_blast(dist, radius_pixels=radius, vital_dodge_pixels=dodge_px)
        if ultimate:
            if blasted:
                dmg = hp
                killed = True
                kills += 1
                in_radius += 1
            else:
                dmg = 0
                killed = False
            results.append(
                {
                    "target_id": t.get("id"),
                    "distance_pixels": dist,
                    "vital_dodge_pixels": dodge_px,
                    "effective_distance_pixels": dist + dodge_px,
                    "in_blast_radius": blasted,
                    "damage_milli": dmg,
                    "killed": killed,
                    "dodge_eligible": dodge_px > 0,
                }
            )
        else:
            in_blast = dist <= radius
            if in_blast:
                in_radius += 1
            if in_blast and hp <= aoe_hit:
                dmg = hp
                killed = True
                kills += 1
            elif in_blast:
                dmg = min(hp, aoe_hit)
                killed = dmg >= hp
                if killed:
                    kills += 1
            else:
                dmg = 0
                killed = False
            results.append(
                {
                    "target_id": t.get("id"),
                    "distance_pixels": dist,
                    "in_blast_radius": in_blast,
                    "damage_milli": dmg,
                    "killed": killed,
                }
            )
    clustered = (
        len(targets) >= coalition_n
        and all(int(t.get("distance_pixels", 0)) <= cluster_max for t in targets)
    )
    return {
        "skill_id": ult_cfg.get("skill_id"),
        "ultimate": ultimate,
        "casts_skill_lock": bool(ult_cfg.get("casts_skill_lock", True)) if ultimate else False,
        "radius_pixels": radius,
        "pure_vital_dodge_pixels": int(ult_cfg.get("dodge", {}).get("pure_vital_dodge_pixels", 10)),
        "dodge_eligible_job_ids": list(ult_cfg.get("dodge", {}).get("eligible_job_ids", [])),
        "targets_in_radius": in_radius,
        "kills": kills,
        "mass_kill_threshold": int(ult_cfg.get("instant_kill_targets_in_radius_min", 10_000)),
        "cluster_wipe": {
            "full_coalition_clustered": clustered and ultimate,
            "full_coalition_count": coalition_n,
            "clustered_max_distance_pixels": cluster_max,
            "note": "10명 전력 집결·산개 없으면 궁극기 전멸",
        },
        "results": results,
    }


def agent_to_combatant(agent: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    preset = agent.get("combatant_preset")
    if preset:
        return build_combatant_snapshot(base_dir=base_dir, preset_id=str(preset))
    if agent.get("world_sovereign_holder") or agent.get("archetype_id") == "npc_arthur_pendragon":
        return build_combatant_snapshot(base_dir=base_dir, preset_id="npc_arthur_pendragon")
    stats = agent.get("stats") or {}
    overrides = {
        "tier": str(agent.get("tier", "mortal")),
        "character_level": int(agent.get("character_level", stats.get("level", 1))),
        "job_id": agent.get("job_id", "wanderer"),
        "job_level": int(agent.get("job_level", 1)),
        "weapon_class": agent.get("weapon_class", "one_handed_sword"),
        "weapon_mastery_level": int(agent.get("weapon_mastery_level", 1)),
        "world_apex_rank": agent.get("world_apex_rank"),
        "label": agent.get("label") or agent.get("archetype_id", "agent"),
    }
    snap = build_combatant_snapshot(base_dir=base_dir, overrides=overrides)
    mhp = int(agent.get("max_hp", 0))
    if mhp > 0:
        snap["hp_milli"] = to_milli(float(mhp), cfg=load_combat_precision_config(base_dir))
    return snap


def _sovereign_strike_damage_milli(
    attacker: dict[str, Any],
    *,
    skill_multiplier: float = 1.0,
) -> dict[str, Any]:
    """아서 — 맥스뎀 유지. 무한 방무이므로 Lv·스킬 무제한 스케일 금지."""
    per_hit = int(attacker.get("pierce_per_hit_milli", 10_000_000))
    max_basic = int(attacker.get("max_damage_per_strike_milli", per_hit))
    max_skill = int(attacker.get("max_skill_damage_per_strike_milli", 50_000_000))
    if skill_multiplier <= 1.0:
        dmg = min(max_basic, per_hit)
    else:
        dmg = min(max_skill, int(per_hit * skill_multiplier))
    return {
        "hit": True,
        "crit": False,
        "sovereign_through": False,
        "damage_milli": dmg,
        "sovereign_capped": True,
        "armor_pierce_milli": dmg,
        "audit": {
            "sovereign_pipeline": True,
            "skill_multiplier": skill_multiplier,
            "max_basic_milli": max_basic,
            "max_skill_milli": max_skill,
        },
    }


def strike_damage_milli(
    attacker: dict[str, Any],
    defender: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: Any,
    skill_multiplier: float = 1.0,
    force_hit: bool | None = None,
    force_sovereign_through: bool | None = None,
) -> dict[str, Any]:
    if attacker.get("world_sovereign"):
        return _sovereign_strike_damage_milli(attacker, skill_multiplier=skill_multiplier)
    cfg = load_combat_precision_config(base_dir)
    atk = dict(attacker)
    if skill_multiplier != 1.0:
        atk["attack_milli"] = int(atk.get("attack_milli", 0) * skill_multiplier)
    return resolve_strike_damage_milli(
        atk,
        defender,
        cfg=cfg,
        rng=rng,
        force_hit=force_hit,
        force_sovereign_through=force_sovereign_through,
    )


def strike_damage_hp(
    attacker: dict[str, Any],
    defender: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: Any,
    skill_multiplier: float = 1.0,
) -> int:
    r = strike_damage_milli(
        attacker, defender, base_dir=base_dir, rng=rng, skill_multiplier=skill_multiplier
    )
    return max(
        0,
        int(round(from_milli(int(r.get("damage_milli", 0)), cfg=load_combat_precision_config(base_dir)))),
    )


def combat_power_estimate(snapshot: dict[str, Any], *, base_dir: str | Path) -> int:
    cfg = load_combat_precision_config(base_dir)
    pierce_dps = int(snapshot.get("pierce_dps_milli", 0)) // fixed_scale(cfg)
    return (
        int(snapshot.get("attack_milli", 0)) // fixed_scale(cfg)
        + pierce_dps
        + int(snapshot.get("character_level", 1))
        + int(snapshot.get("weapon_mastery_level", 1))
    )


def sovereign_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    from utils.sovereign_siege import sovereign_siege_status
    from utils.sovereign_wish import wish_status

    bundle = load_combat_bundle(base_dir)
    arthur = build_combatant_snapshot(base_dir=base_dir, preset_id="npc_arthur_pendragon")
    status = sovereign_siege_status(state, base_dir=base_dir)
    status["wish"] = wish_status(state, base_dir=base_dir)
    status["arthur_snapshot"] = {
        "hp_milli": arthur["hp_milli"],
        "pierce_dps_milli": arthur.get("pierce_dps_milli"),
        "pierce_per_hit_milli": arthur.get("pierce_per_hit_milli"),
        "max_damage_per_strike_milli": arthur.get("max_damage_per_strike_milli"),
        "max_skill_damage_per_strike_milli": arthur.get("max_skill_damage_per_strike_milli"),
        "sovereign_damage_capped": arthur.get("sovereign_damage_capped"),
        "elite_melee_ttk_seconds": arthur.get("elite_melee_ttk_seconds"),
        "combat_power": combat_power_estimate(arthur, base_dir=base_dir),
    }
    status["excalibur_ultimate"] = bundle["scaling"].get("excalibur_ultimate", {})
    status["elite_coalition"] = elite_coalition_pierce_dps(bundle=bundle)
    return status
