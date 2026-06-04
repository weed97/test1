"""Rule-based combat and exploration resolution (fallback / hybrid mechanical layer)."""

from __future__ import annotations

import copy
import random
from typing import Any, Optional

from utils.dice import roll_d20

TIME_CYCLE = ["morning", "afternoon", "evening", "night"]
ELEMENT_STRONG = 1.5
ELEMENT_WEAK = 0.5

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


class RuleEngine:
    def __init__(self, state: dict[str, Any], rng: random.Random) -> None:
        self.state = state
        self.rng = rng

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
        mults = [_ELEMENT_CHART.get((attack_element, d), 1.0) for d in defense_elements]
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

    def start_combat(self, enemy: dict[str, Any], party: list[dict[str, Any]], turn: int) -> None:
        self.state["combat"] = {
            "round": 1,
            "enemy_id": enemy["id"],
            "allies": {c["id"]: c for c in party},
            "enemies": {enemy["id"]: enemy},
            "log": [],
        }

    def run_combat_round(self, turn: int) -> dict[str, Any]:
        combat = self.state.get("combat")
        if not combat:
            return {"lines": ["(전투 없음)"], "summary": "no combat"}

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

        for side, actor, _ in participants:
            if actor["stats"]["hp"] <= 0:
                continue
            target_pool = (
                [c for c in combat["enemies"].values() if c["stats"]["hp"] > 0]
                if side == "ally"
                else [c for c in combat["allies"].values() if c["stats"]["hp"] > 0]
            )
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
        mechanical: dict[str, Any] = {
            "lines": lines,
            "round": combat["round"] - 1,
            "combat": copy.deepcopy(combat),
            "character_updates": {},
            "event_log_append": [],
        }

        allies_down = all(c["stats"]["hp"] <= 0 for c in combat["allies"].values())
        enemies_down = all(c["stats"]["hp"] <= 0 for c in combat["enemies"].values())

        if allies_down or enemies_down:
            winner = "enemies" if allies_down else "allies"
            summary = "패배..." if allies_down else "승리!"
            lines.append(f"전투 종료 — {summary}")
            mechanical["event_log_append"] = [
                {"turn": turn, "type": "combat_end", "summary": summary, "winner": winner}
            ]
            for cid, char in combat["allies"].items():
                mechanical["character_updates"][cid] = {"stats": char["stats"]}
            mechanical["combat"] = None
            self.state["combat"] = None
            if winner == "allies":
                self.state["world"]["tension"] = max(0.0, self.state["world"].get("tension", 0) - 0.05)
            else:
                self.state["world"]["tension"] = min(1.0, self.state["world"].get("tension", 0) + 0.15)

        mechanical["summary"] = lines[-1] if lines else "combat round"
        return mechanical

    def run_exploration(self, turn: int) -> dict[str, Any]:
        world = self.state["world"]
        tension = world.get("tension", 0)
        natural, _ = roll_d20(0, self.rng)
        event_log_append: list[dict[str, Any]] = []

        if natural >= 18:
            world["tension"] = min(1.0, tension + 0.1)
            summary = "정찰 중 그림자 군단의 흔적을 발견했다."
            self.state["flags"]["shadow_legion_spotted"] = True
        elif natural <= 5:
            gold = self.rng.randint(5, 25)
            self.state["inventory"]["party_gold"] = self.state["inventory"].get("party_gold", 0) + gold
            summary = f"버려진 상자에서 {gold} 골드를 획득했다."
        else:
            summary = "별다른 사건 없이 주변을 정찰했다."

        event_log_append.append({"turn": turn, "type": "explore", "summary": summary})
        return {"summary": summary, "event_log_append": event_log_append}

    def run_rest(self, turn: int, loader: Any) -> dict[str, Any]:
        for cid in self.state.get("party", []):
            char = loader.load_character(cid)
            char["stats"]["hp"] = char["stats"]["max_hp"]
            char["stats"]["mana"] = char["stats"]["max_mana"]
            loader.apply_character_updates(self.state, {cid: {"stats": char["stats"]}})
        summary = "파티가 휴식하여 HP와 마나를 회복했다."
        return {
            "summary": summary,
            "event_log_append": [{"turn": turn, "type": "rest", "summary": summary}],
        }
