"""Inter-agent competition — monster civilizations, NPC prosperity, rivalries."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from utils.config_loader import load_config
from utils.ecology_state import ecology_flags


def load_civ_config(base_dir: str | Path) -> dict[str, Any]:
    return load_config(base_dir, "monster_civilizations.json")


def get_civilization_state(state: dict[str, Any], civ_id: str) -> dict[str, Any]:
    civs = ecology_flags(state).setdefault("civilizations", {})
    if civ_id not in civs:
        civs[civ_id] = {"prosperity": 0, "stage_id": None, "wins": 0, "losses": 0}
    return civs[civ_id]


def civilization_id_for_agent(agent: dict[str, Any], cfg: dict[str, Any]) -> str | None:
    if agent.get("civilization_id"):
        return str(agent["civilization_id"])
    chain = agent.get("evolution_chain") or agent.get("species_id")
    if chain:
        return cfg.get("evolution_chain_to_civ", {}).get(chain)
    if agent.get("kind") == "npc" and agent.get("map_id") == "ashpoint_01":
        return "ashpoint_commons"
    return None


def attach_society(agent: dict[str, Any], *, base_dir: str | Path) -> None:
    cfg = load_civ_config(base_dir)
    civ_id = civilization_id_for_agent(agent, cfg)
    if not civ_id:
        return
    agent["civilization_id"] = civ_id
    agent.setdefault("prosperity", 0)
    defs = cfg.get("civilizations", {}).get(civ_id) or cfg.get("npc_societies", {}).get(civ_id)
    if defs:
        agent["culture_tags"] = list(defs.get("culture_tags", []))


def _civ_stage(cfg: dict[str, Any], civ_id: str, prosperity: int) -> str:
    defs: dict[str, Any] = {}
    for key in (
        "civilizations",
        "npc_societies",
        "player_civilizations",
        "off_map_civilizations",
    ):
        defs = cfg.get(key, {}).get(civ_id) or defs
        if defs:
            break
    stage_id = "unknown"
    for st in defs.get("stages", []):
        if prosperity >= int(st.get("prosperity", 0)):
            stage_id = st["id"]
    return stage_id


def _agent_power(agent: dict[str, Any]) -> int:
    tier = int(agent.get("evolution_tier", 1))
    plunder = agent.get("plunder") or {}
    return (
        int(agent.get("hp", 20))
        + int(plunder.get("power_bonus", 0))
        + tier * 12
        + int(agent.get("prosperity", 0)) // 5
    )


def _manhattan(a: dict[str, Any], b: dict[str, Any]) -> int:
    return abs(int(a["x"]) - int(b["x"])) + abs(int(a["y"]) - int(b["y"]))


def tick_rivalries(
    agents: list[dict[str, Any]],
    *,
    base_dir: str | Path,
    state: dict[str, Any],
    rng: random.Random,
) -> list[str]:
    """Monsters of rival civilizations contest territory and prosperity."""
    cfg = load_civ_config(base_dir)
    comp = cfg.get("competition", {})
    max_events = int(comp.get("max_rivalry_events_per_tick", 2))
    rng_tiles = int(comp.get("rivalry_range_tiles", 2))
    dmg_base = int(comp.get("monster_vs_monster_damage_base", 10))
    lines: list[str] = []
    import json as _json
    from pathlib import Path as _Path

    pack_path = _Path(base_dir) / "config" / "monster_pack_behavior.json"
    pcfg: dict[str, Any] = {}
    if pack_path.is_file():
        with pack_path.open(encoding="utf-8") as f:
            pcfg = _json.load(f)
    max_internal = int(pcfg.get("internal_duels", {}).get("max_per_map_tick", 3))

    monsters = [a for a in agents if a.get("kind") == "monster" and a.get("civilization_id")]
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for i, a in enumerate(monsters):
        for b in monsters[i + 1 :]:
            if _manhattan(a, b) > rng_tiles:
                continue
            ca, cb = a.get("civilization_id"), b.get("civilization_id")
            if not ca or not cb:
                continue
            if ca == cb:
                pairs.append((a, b))
                continue
            civ_a = cfg.get("civilizations", {}).get(ca, {})
            if cb in civ_a.get("rivals", []):
                pairs.append((a, b))

    internal_cap = max_internal

    rng.shuffle(pairs)

    def _pair_sort_key(pair: tuple[dict[str, Any], dict[str, Any]]) -> float:
        a, b = pair
        same = a.get("civilization_id") == b.get("civilization_id")
        return (0 if same else 1, -_agent_power(a) - _agent_power(b))

    pairs.sort(key=_pair_sort_key)

    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for pair in pairs:
        if len(selected) >= max_events:
            break
        a, b = pair
        same_civ = a.get("civilization_id") == b.get("civilization_id")
        if same_civ and internal_cap <= 0:
            continue
        selected.append(pair)
        if same_civ:
            internal_cap -= 1

    for a, b in selected:
        pa, pb = _agent_power(a), _agent_power(b)
        roll = rng.random() * (pa + pb)
        winner, loser = (a, b) if roll < pa else (b, a)
        dmg = dmg_base + rng.randint(0, 6)
        loser["hp"] = int(loser.get("hp", 20)) - dmg
        w_civ = str(winner.get("civilization_id", ""))
        l_civ = str(loser.get("civilization_id", ""))
        w_def = cfg.get("civilizations", {}).get(w_civ, {})
        gain = int(w_def.get("prosperity_per_rival_win", 10))
        ws = get_civilization_state(state, w_civ)
        ls = get_civilization_state(state, l_civ)
        ws["prosperity"] = int(ws.get("prosperity", 0)) + gain
        ws["wins"] = int(ws.get("wins", 0)) + 1
        ls["losses"] = int(ls.get("losses", 0)) + 1
        ws["stage_id"] = _civ_stage(cfg, w_civ, int(ws["prosperity"]))
        w_lab = winner.get("label") or w_civ
        l_lab = loser.get("label") or l_civ
        same_civ = a.get("civilization_id") == b.get("civilization_id")
        if same_civ:
            lines.append(
                f"[내부전] {w_lab}이(가) 같은 무리의 {l_lab}을(를) 격파했다. (+지배, 번영 {gain})"
            )
        else:
            lines.append(
                f"[경쟁] {w_lab} 무리가 {l_lab} 무리와 영역 다툼에서 이겼다. (+번영 {gain})"
            )
        if int(loser["hp"]) <= 0:
            lines.append(f"[경쟁] {l_lab} 개체가 쓰러져 무리가 물러난다.")
            from utils.monster_pack import apply_monster_kill_growth

            lines.extend(
                apply_monster_kill_growth(winner, loser, agents, base_dir=base_dir, state=state)
            )
            agents_ref = state.get("flags", {}).get("ecology", {}).get("agents", [])
            if loser in agents_ref:
                agents_ref.remove(loser)
    return lines


def tick_npc_competition(
    agents: list[dict[str, Any]],
    *,
    base_dir: str | Path,
    state: dict[str, Any],
) -> list[str]:
    """NPC settlements compete for prosperity; predator wins drain commons."""
    cfg = load_civ_config(base_dir)
    lines: list[str] = []
    builders = [a for a in agents if a.get("ai") == "builder" and a.get("settlement")]
    society_id = "ashpoint_commons"
    soc = get_civilization_state(state, society_id)
    total_build = sum(int(a.get("settlement", {}).get("build_points", 0)) for a in builders)
    if builders:
        soc["prosperity"] = int(soc.get("prosperity", 0)) + min(8, total_build // 20)
        soc["stage_id"] = _civ_stage(cfg, society_id, int(soc["prosperity"]))
    if len(builders) >= 2:
        ranked = sorted(
            builders,
            key=lambda a: int(a.get("settlement", {}).get("build_points", 0)),
            reverse=True,
        )
        lead = ranked[0]
        trail = ranked[1]
        slowdown = int(
            cfg.get("npc_societies", {}).get(society_id, {}).get("rivalry_slowdown", 3)
        )
        trail_settle = trail.setdefault("settlement", {})
        trail_settle["build_points"] = max(
            0, int(trail_settle.get("build_points", 0)) - slowdown
        )
        lead_name = lead.get("archetype_id", "npc")
        lines.append(
            f"[번영] 마을 경쟁: {lead_name} 쪽이 앞서고, 라이벌 거점은 자원 압박을 받는다."
        )
    decay = int(cfg.get("competition", {}).get("prosperity_decay_if_predator_wins", 5))
    eco = ecology_flags(state)
    if eco.get("last_predator_npc_kill"):
        soc["prosperity"] = max(0, int(soc.get("prosperity", 0)) - decay)
        eco["last_predator_npc_kill"] = False
        lines.append(f"[번영] 습격 여파로 공동체 번영이 {decay} 감소했다.")
    return lines


def tick_civilization_prosperity(
    state: dict[str, Any],
    agents: list[dict[str, Any]],
    *,
    base_dir: str | Path,
) -> list[str]:
    """Sync monster civ prosperity from plunder and stage-ups."""
    cfg = load_civ_config(base_dir)
    lines: list[str] = []
    for civ_id, defs in cfg.get("civilizations", {}).items():
        members = [a for a in agents if a.get("civilization_id") == civ_id]
        if not members:
            continue
        cs = get_civilization_state(state, civ_id)
        old_stage = cs.get("stage_id")
        cs["stage_id"] = _civ_stage(cfg, civ_id, int(cs["prosperity"]))
        if cs["stage_id"] != old_stage and old_stage is not None:
            label = defs.get("label", civ_id)
            for st in defs.get("stages", []):
                if st["id"] == cs["stage_id"]:
                    lines.append(f"[문명] {label}이(가) 「{st.get('label', cs['stage_id'])}」 단계로 성장했다.")
                    break
    return lines


def tick_agent_competition(
    state: dict[str, Any],
    map_id: str,
    *,
    base_dir: str | Path,
    rng: random.Random | None = None,
) -> list[str]:
    eco = ecology_flags(state)
    agents = [a for a in eco.get("agents", []) if a.get("map_id") == map_id]
    r = rng or random.Random()
    lines: list[str] = []
    lines.extend(tick_rivalries(agents, base_dir=base_dir, state=state, rng=r))
    lines.extend(tick_npc_competition(agents, base_dir=base_dir, state=state))
    lines.extend(tick_civilization_prosperity(state, agents, base_dir=base_dir))
    return lines
