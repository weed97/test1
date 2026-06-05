"""Monster packs — greed, internal rivalry, alpha dominance, pack power growth."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


def load_pack_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "monster_pack_behavior.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _manhattan(a: dict[str, Any], b: dict[str, Any]) -> int:
    return abs(int(a["x"]) - int(b["x"])) + abs(int(a["y"]) - int(b["y"]))


def ensure_pack_block(agent: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    if agent.get("kind") != "monster":
        return {}
    pcfg = load_pack_config(base_dir)
    pack = agent.setdefault(
        "pack",
        {
            "role": "grunt",
            "dominance": 0,
            "greed": int(pcfg.get("greed", {}).get("default", 74)),
            "kills": 0,
        },
    )
    intel = agent.setdefault("intelligence", {})
    intel.setdefault("disposition", "greedy")
    return pack


def refresh_pack_alphas(agents: list[dict[str, Any]], *, base_dir: str | Path) -> None:
    """Strongest dominance per civilization_id becomes alpha (others grunt)."""
    by_civ: dict[str, list[dict[str, Any]]] = {}
    for a in agents:
        if a.get("kind") != "monster":
            continue
        cid = a.get("civilization_id")
        if not cid:
            continue
        ensure_pack_block(a, base_dir=base_dir)
        by_civ.setdefault(str(cid), []).append(a)

    for _civ, members in by_civ.items():
        if not members:
            continue
        for m in members:
            m["pack"]["role"] = "grunt"
        alpha = max(
            members,
            key=lambda m: (
                int(m.get("pack", {}).get("dominance", 0)),
                int(m.get("evolution_tier", 1)),
                int(m.get("hp", 0)),
            ),
        )
        alpha["pack"]["role"] = "alpha"


def apply_monster_kill_growth(
    winner: dict[str, Any],
    loser: dict[str, Any],
    others: list[dict[str, Any]],
    *,
    base_dir: str | Path,
    state: dict[str, Any],
) -> list[str]:
    """Winner grows; pack shares power; civilization may overextend."""
    lines: list[str] = []
    if winner.get("kind") != "monster" or loser.get("kind") != "monster":
        return lines

    pcfg = load_pack_config(base_dir)
    pk = pcfg.get("pack", {})
    gr = pcfg.get("greed", {})
    wpack = ensure_pack_block(winner, base_dir=base_dir)
    wpack["kills"] = int(wpack.get("kills", 0)) + 1
    wpack["greed"] = min(
        int(gr.get("max", 98)),
        int(wpack.get("greed", 70)) + int(gr.get("per_plunder_victim", 4)),
    )
    was_alpha = loser.get("pack", {}).get("role") == "alpha"
    gain = int(pk.get("alpha_dominance_per_kill", 10))
    if was_alpha:
        gain += 8
    wpack["dominance"] = int(wpack.get("dominance", 0)) + gain

    pl = winner.setdefault("plunder", {})
    pl["power_bonus"] = int(pl.get("power_bonus", 0)) + 2
    if was_alpha:
        pl["power_bonus"] = int(pl.get("power_bonus", 0)) + 4

    radius = int(pk.get("pack_plunder_share_radius", 3))
    share = int(pk.get("grunt_growth_on_alpha_kill", 4)) if was_alpha else int(
        pk.get("alpha_growth_on_grunt_kill", 2)
    )
    civ = winner.get("civilization_id")
    w_label = winner.get("label") or "몬스터"
    l_label = loser.get("label") or "라이벌"

    for o in others:
        if o["instance_id"] in (winner["instance_id"], loser["instance_id"]):
            continue
        if o.get("kind") != "monster" or o.get("civilization_id") != civ:
            continue
        if _manhattan(winner, o) > radius:
            continue
        op = ensure_pack_block(o, base_dir=base_dir)
        op["dominance"] = int(op.get("dominance", 0)) + share
        pl_o = o.setdefault("plunder", {})
        pl_o["power_bonus"] = int(pl_o.get("power_bonus", 0)) + 1

    lines.append(
        f"[무리] {w_label}이(가) {l_label}을(를) 제압 — 지배 {wpack['dominance']}, 탐욕 {wpack['greed']}"
    )
    if was_alpha:
        lines.append(f"[무리] 우두머리 교체 — {w_label} 무리가 더 강해진다.")

    if int(wpack.get("dominance", 0)) >= int(pk.get("overdominance_threshold", 85)):
        from utils.agent_competition import get_civilization_state

        civ_id = winner.get("civilization_id")
        if civ_id:
            cs = get_civilization_state(state, civ_id)
            pen = int(pk.get("civ_prosperity_penalty_on_collapse", 12))
            cs["prosperity"] = max(5, int(cs.get("prosperity", 0)) - pen)
            wpack["dominance"] = max(0, int(wpack["dominance"]) - 20)
            lines.append(
                f"[무리·자멸] 탐욕 과다 — {civ_id} 문명이 내부 싸움으로 번영 {pen} 하락."
            )

    refresh_pack_alphas(
        [a for a in others if a.get("map_id") == winner.get("map_id")] + [winner],
        base_dir=base_dir,
    )
    return lines
