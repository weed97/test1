#!/usr/bin/env python3
"""Fantasy Simulator — main orchestration loop.

Loads world_state.json, applies rule-based turn resolution, and persists updates.
Prompts in prompts/ are exposed for LLM integration; this engine runs standalone
with deterministic dice logic (stdlib only).

Usage:
    python simulation_engine.py
    python simulation_engine.py --turns 3 --seed 42
    python simulation_engine.py --action explore
    python simulation_engine.py --combat malachar_voidweaver
    python simulation_engine.py --show-prompts
    python simulation_engine.py --status
"""

from __future__ import annotations

import argparse
import copy
import random
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from utils.dice import roll_d20  # noqa: E402
from utils.state_loader import StateLoader  # noqa: E402

TIME_CYCLE = ["morning", "afternoon", "evening", "night"]
ELEMENT_STRONG = 1.5
ELEMENT_WEAK = 0.5

# Simplified element chart keyed as (attack, defense) -> multiplier
_ELEMENT_CHART: dict[tuple[str, str], float] = {
    ("fire", "water"): ELEMENT_WEAK,
    ("fire", "air"): ELEMENT_STRONG,
    ("fire", "shadow"): ELEMENT_STRONG,
    ("water", "fire"): ELEMENT_STRONG,
    ("water", "earth"): ELEMENT_WEAK,
    ("water", "light"): ELEMENT_STRONG,
    ("earth", "fire"): 1.0,
    ("earth", "water"): ELEMENT_STRONG,
    ("earth", "air"): ELEMENT_WEAK,
    ("earth", "shadow"): ELEMENT_STRONG,
    ("air", "fire"): ELEMENT_WEAK,
    ("air", "earth"): ELEMENT_STRONG,
    ("air", "shadow"): ELEMENT_WEAK,
    ("light", "water"): ELEMENT_WEAK,
    ("light", "shadow"): ELEMENT_STRONG,
    ("shadow", "fire"): ELEMENT_WEAK,
    ("shadow", "earth"): ELEMENT_WEAK,
    ("shadow", "air"): ELEMENT_STRONG,
}


class SimulationEngine:
    """Turn-based fantasy world orchestrator."""

    def __init__(
        self,
        loader: StateLoader,
        *,
        seed: Optional[int] = None,
    ) -> None:
        self.loader = loader
        self.rng = random.Random(seed)
        self.state = loader.load_world_state()
        self.turn = len(self.state.get("event_log", []))

    def advance_time(self) -> str:
        world = self.state["world"]
        idx = TIME_CYCLE.index(world.get("time_of_day", "morning"))
        if idx >= len(TIME_CYCLE) - 1:
            world["day"] = world.get("day", 1) + 1
            world["time_of_day"] = TIME_CYCLE[0]
        else:
            world["time_of_day"] = TIME_CYCLE[idx + 1]
        return world["time_of_day"]

    def _element_multiplier(self, attack_element: str, defense_elements: list[str]) -> float:
        if not attack_element or not defense_elements:
            return 1.0
        mults = []
        for defense in defense_elements:
            mults.append(_ELEMENT_CHART.get((attack_element, defense), 1.0))
        return sum(mults) / len(mults)

    def resolve_attack(
        self,
        attacker: dict[str, Any],
        defender: dict[str, Any],
        *,
        spell: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        atk_mod = attacker["modifiers"].get("spellcasting" if spell else "attack", 0)
        def_mod = defender["modifiers"].get("defense", 0)
        natural, total = roll_d20(atk_mod, self.rng)
        dc = 10 + def_mod

        result: dict[str, Any] = {
            "attacker": attacker["id"],
            "defender": defender["id"],
            "natural": natural,
            "roll": total,
            "dc": dc,
            "hit": False,
            "damage": 0,
            "critical": natural == 20,
            "fumble": natural == 1,
        }

        if natural == 1:
            return result

        if total >= dc or natural == 20:
            result["hit"] = True
            if spell:
                power = spell.get("power", 10)
                element = spell.get("element", "")
                mult = self._element_multiplier(element, defender.get("elements", []))
                if element == "shadow" and self.state["world"].get("tension", 0) >= 0.5:
                    mult *= 1.2
                damage = int(power * mult)
                mana_cost = spell.get("mana_cost", 0)
                attacker["stats"]["mana"] = max(0, attacker["stats"]["mana"] - mana_cost)
            else:
                weapon = attacker.get("equipment", {}).get("weapon", {})
                damage = weapon.get("damage", 4) + attacker["modifiers"].get("attack", 0) // 2

            reduction = defender.get("equipment", {}).get("armor", {}).get("reduction", 0)
            final = max(1, damage - reduction)
            if natural == 20:
                final *= 2
            defender["stats"]["hp"] = max(0, defender["stats"]["hp"] - final)
            result["damage"] = final

        return result

    def start_combat(self, enemy_id: str) -> None:
        enemy = copy.deepcopy(self.loader.load_character(enemy_id))
        party = [copy.deepcopy(c) for c in self.loader.load_party(self.state)]
        self.state["combat"] = {
            "round": 1,
            "enemy_id": enemy_id,
            "allies": {c["id"]: c for c in party},
            "enemies": {enemy_id: enemy},
            "log": [],
        }
        self.loader.append_event_log(
            self.state,
            {
                "turn": self.turn,
                "type": "combat_start",
                "summary": f"전투 시작: {enemy['name']}",
            },
        )

    def run_combat_round(self) -> list[str]:
        combat = self.state.get("combat")
        if not combat:
            return ["(전투 없음)"]

        lines: list[str] = []
        participants: list[tuple[str, dict[str, Any], str]] = []
        for cid, char in combat["allies"].items():
            participants.append(("ally", char, cid))
        for cid, char in combat["enemies"].items():
            participants.append(("enemy", char, cid))

        participants.sort(
            key=lambda item: roll_d20(item[1]["modifiers"].get("agility", 0), self.rng)[1],
            reverse=True,
        )

        for side, actor, actor_id in participants:
            if actor["stats"]["hp"] <= 0:
                continue

            if side == "ally":
                target_pool = [c for c in combat["enemies"].values() if c["stats"]["hp"] > 0]
            else:
                target_pool = [c for c in combat["allies"].values() if c["stats"]["hp"] > 0]

            if not target_pool:
                break

            target = self.rng.choice(target_pool)
            spell = None
            if actor.get("spells") and actor["stats"]["mana"] >= 12:
                spell = self.rng.choice(actor["spells"])
            outcome = self.resolve_attack(actor, target, spell=spell)
            spell_name = spell["name"] if spell and outcome["hit"] else "공격"
            line = (
                f"R{combat['round']} {actor['name']} → {target['name']}: "
                f"{spell_name} roll={outcome['roll']} "
                f"{'HIT' if outcome['hit'] else 'MISS'}"
                + (f" dmg={outcome['damage']}" if outcome.get("damage") else "")
            )
            lines.append(line)
            combat["log"].append(line)

        combat["round"] += 1

        allies_down = all(c["stats"]["hp"] <= 0 for c in combat["allies"].values())
        enemies_down = all(c["stats"]["hp"] <= 0 for c in combat["enemies"].values())

        if allies_down or enemies_down:
            winner = "enemies" if allies_down else "allies"
            summary = "패배..." if allies_down else "승리!"
            lines.append(f"전투 종료 — {summary}")
            self.loader.append_event_log(
                self.state,
                {"turn": self.turn, "type": "combat_end", "summary": summary, "winner": winner},
            )
            updates = {}
            for cid, char in combat["allies"].items():
                updates[cid] = {"stats": char["stats"]}
            self.loader.apply_character_updates(self.state, updates)
            self.state["combat"] = None
            if winner == "allies":
                self.state["world"]["tension"] = max(
                    0.0, self.state["world"].get("tension", 0) - 0.05
                )
            else:
                self.state["world"]["tension"] = min(
                    1.0, self.state["world"].get("tension", 0) + 0.15
                )

        return lines

    def run_exploration(self) -> str:
        world = self.state["world"]
        tension = world.get("tension", 0)
        natural, total = roll_d20(0, self.rng)
        if natural >= 18:
            world["tension"] = min(1.0, tension + 0.1)
            summary = "정찰 중 그림자 군단의 흔적을 발견했다."
            self.state["flags"]["shadow_legion_spotted"] = True
        elif natural <= 5:
            gold = self.rng.randint(5, 25)
            self.state["inventory"]["party_gold"] = (
                self.state["inventory"].get("party_gold", 0) + gold
            )
            summary = f"버려진 상자에서 {gold} 골드를 획득했다."
        else:
            summary = "별다른 사건 없이 주변을 정찰했다."
        self.loader.append_event_log(
            self.state, {"turn": self.turn, "type": "explore", "summary": summary}
        )
        return summary

    def run_turn(self, action: str = "explore") -> dict[str, Any]:
        self.turn += 1
        time_label = self.advance_time()
        outcome_lines: list[str] = []

        if action == "combat" and not self.state.get("combat"):
            self.start_combat("malachar_voidweaver")
            outcome_lines.append("말라카르와의 전투가 시작되었다!")
        elif self.state.get("combat"):
            outcome_lines.extend(self.run_combat_round())
        elif action == "explore":
            outcome_lines.append(self.run_exploration())
        elif action == "rest":
            for cid in self.state.get("party", []):
                char = self.loader.load_character(cid)
                char["stats"]["hp"] = char["stats"]["max_hp"]
                char["stats"]["mana"] = char["stats"]["max_mana"]
                self.loader.apply_character_updates(self.state, {cid: {"stats": char["stats"]}})
            outcome_lines.append("파티가 휴식하여 HP와 마나를 회복했다.")
            self.loader.append_event_log(
                self.state, {"turn": self.turn, "type": "rest", "summary": outcome_lines[-1]}
            )
        else:
            outcome_lines.append(f"알 수 없는 행동: {action}")

        self.loader.save_world_state(self.state)
        return {
            "turn": self.turn,
            "time": time_label,
            "day": self.state["world"]["day"],
            "lines": outcome_lines,
        }

    def status_report(self) -> str:
        world = self.state["world"]
        lines = [
            f"=== {world['name']} | Day {world['day']} ({world['time_of_day']}) ===",
            f"위치: {world['location']}",
            f"날씨: {world['weather']} | 긴장도: {world.get('tension', 0):.2f}",
            f"골드: {self.state.get('inventory', {}).get('party_gold', 0)}",
            "",
            "파티:",
        ]
        for cid in self.state.get("party", []):
            c = self.loader.load_character(cid)
            if self.state.get("combat") and cid in self.state["combat"]["allies"]:
                stats = self.state["combat"]["allies"][cid]["stats"]
            else:
                stats = c["stats"]
            lines.append(
                f"  - {c['name']}: HP {stats['hp']}/{stats['max_hp']} "
                f"MP {stats['mana']}/{stats['max_mana']}"
            )
        if self.state.get("combat"):
            lines.append("")
            lines.append("(전투 진행 중)")
        if self.state.get("event_log"):
            lines.append("")
            lines.append("최근 이벤트:")
            for ev in self.state["event_log"][-5:]:
                lines.append(f"  [{ev.get('type')}] {ev.get('summary')}")
        return "\n".join(lines)

    def get_prompt_bundle(self) -> dict[str, str]:
        return {role: self.loader.load_prompt(role) for role in self.loader.list_prompts()}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fantasy Simulator — orchestration engine")
    p.add_argument("--root", default=str(ROOT), help="fantasy_simulator 디렉터리 경로")
    p.add_argument("--turns", type=int, default=1, help="실행할 턴 수")
    p.add_argument("--seed", type=int, default=None, help="난수 시드")
    p.add_argument(
        "--action",
        choices=["explore", "rest", "combat"],
        default="explore",
        help="턴 행동",
    )
    p.add_argument("--status", action="store_true", help="현재 상태 출력 후 종료")
    p.add_argument("--show-prompts", action="store_true", help="역할별 프롬프트 목록 출력")
    p.add_argument("--combat", metavar="ENEMY_ID", help="지정 적과 전투 시작 후 진행")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    loader = StateLoader.from_package_root(args.root)
    engine = SimulationEngine(loader, seed=args.seed)

    if args.show_prompts:
        for role, text in engine.get_prompt_bundle().items():
            print(f"--- prompts/{role}.txt ({len(text)} chars) ---")
            print(text[:400] + ("..." if len(text) > 400 else ""))
            print()
        return 0

    if args.status:
        print(engine.status_report())
        return 0

    action = "combat" if args.combat else args.action
    if args.combat:
        engine.start_combat(args.combat)
        engine.loader.save_world_state(engine.state)

    for _ in range(args.turns):
        result = engine.run_turn(action=action)
        print(f"\n[Turn {result['turn']}] Day {result['day']} — {result['time']}")
        for line in result["lines"]:
            print(f"  {line}")
        if action == "combat" and not engine.state.get("combat"):
            action = "explore"

    print("\n" + engine.status_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
