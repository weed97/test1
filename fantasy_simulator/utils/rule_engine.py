"""Rule-based combat and exploration resolution (fallback / hybrid mechanical layer)."""

from __future__ import annotations

import copy
import random
from typing import TYPE_CHECKING, Any, Optional

from utils.dice import roll_d20

if TYPE_CHECKING:
    from utils.event_engine import EventEngine

TIME_CYCLE = ["morning", "afternoon", "evening", "night"]
TIME_TO_CYCLE: dict[str, str] = {
    "morning": "morning",
    "아침": "morning",
    "오전": "morning",
    "afternoon": "afternoon",
    "낮": "afternoon",
    "오후": "afternoon",
    "evening": "evening",
    "저녁": "evening",
    "night": "night",
    "밤": "night",
    "한밤": "night",
}
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
    def __init__(
        self,
        state: dict[str, Any],
        rng: random.Random,
        *,
        event_engine: EventEngine | None = None,
    ) -> None:
        self.state = state
        self.rng = rng
        self.event_engine = event_engine

    def advance_time(self) -> str:
        world = self.state["world"]
        raw = world.get("time_of_day", "morning")
        current = TIME_TO_CYCLE.get(raw, raw if raw in TIME_CYCLE else "morning")
        world["time_of_day"] = current
        idx = TIME_CYCLE.index(current)
        if idx >= len(TIME_CYCLE) - 1:
            world["day"] = world.get("day", 1) + 1
            world["time_of_day"] = TIME_CYCLE[0]
        else:
            world["time_of_day"] = TIME_CYCLE[idx + 1]
        return world["time_of_day"]

    def _tension(self) -> int:
        return int(self.state.get("world", {}).get("tension", 42))

    def _adjust_tension(self, delta: int) -> None:
        world = self.state.setdefault("world", {})
        world["tension"] = max(0, min(100, self._tension() + delta))

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
                if element == "shadow" and self._tension() >= 50:
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
                self._adjust_tension(-8)
                enemy_id = combat.get("enemy_id", "")
                flags = self.state.setdefault("flags", {})
                if enemy_id == "rune_sentinel":
                    flags["rune_sentinel_defeated"] = True
                    flags["seal_fragment_obtained"] = True
                    lines.append("봉인 파편 조각을 손에 넣었다. 실버 스토커와의 전투 준비가 되었다.")
                    self._adjust_tension(-5)
                if enemy_id == "silver_stalker" and self.event_engine:
                    quest = self.state.setdefault("flags", {}).setdefault("quests", {})
                    if quest.get("active") == "smoke_on_the_mountain":
                        quest["stage"] = 4
                        catalog = self.event_engine.content.load_quests()
                        q = catalog.get("smoke_on_the_mountain")
                        if q:
                            self.event_engine._complete_quest(self.state, q)
            else:
                self._adjust_tension(12)

        mechanical["summary"] = lines[-1] if lines else "combat round"
        return mechanical

    def run_exploration(self, turn: int) -> dict[str, Any]:
        if self.event_engine:
            triggered = self.event_engine.try_trigger_event(self.state, "explore", turn)
            if triggered:
                return triggered

        world = self.state["world"]
        natural, _ = roll_d20(0, self.rng)
        tension = self._tension()
        zone = self.event_engine._location_zone(self.state) if self.event_engine else "ashpoint"

        if zone == "tower":
            if self.event_engine:
                self.event_engine.main_story.record_mountain_visit(self.state, found=True)
            if natural >= 15:
                summary = "관측탑 2층으로 이어지는 계단이 보인다. 봉인 파편 없이는 올라가기 위험하다."
            elif natural <= 5:
                summary = "바닥의 검은 액체가 발밑까지 번졌다. 급히 물러선다."
                self._adjust_tension(5)
            else:
                summary = "탑 내부에서 금속이 긁히는 소리. 룬 센티넬이 아직 깨어 있는 것 같다."
        elif zone == "forest":
            if self.event_engine:
                self.event_engine.main_story.record_mountain_visit(
                    self.state,
                    found=bool(self.state.get("flags", {}).get("tower_sighted")),
                )
            if natural >= 18:
                summary = "나무 사이로 옛 관측탑의 윤곽이 보인다. investigate tower 또는 explore."
                self.state.setdefault("flags", {})["tower_sighted"] = True
            elif natural <= 5:
                summary = "숲 안개 속에서 무언가가 따라오는 기분. tension 상승."
                self._adjust_tension(6)
            else:
                summary = "짙은 숲길. 발밑 이끼에 실버우드 룬 조각이 박혀 있다."
        elif natural >= 18:
            self._adjust_tension(8)
            summary = "정찰 중 숲 쪽에서 검은 연기와 발자국을 발견했다."
            self.state.setdefault("flags", {})["smoke_trail_spotted"] = True
        elif natural <= 5:
            gold = self.rng.randint(8, 30)
            self.state["inventory"]["party_gold"] = self.state["inventory"].get("party_gold", 0) + gold
            summary = f"버려진 상자에서 {gold} 골드를 획득했다."
        elif tension >= 60:
            summary = "마을 사람들이 불안한 눈으로 숲 쪽을 바라본다. 긴장감이 감돈다."
        else:
            summary = "애쉬포인트 거리를 돌며 별다른 변화는 없었다."

        return {
            "summary": summary,
            "event_log_append": [{"turn": turn, "type": "explore", "summary": summary}],
        }

    def run_social(self, action: str, turn: int, loader: Any) -> dict[str, Any]:
        if self.event_engine:
            return self.event_engine.talk(self.state, action, turn, loader)
        return {"summary": "대화 상대를 찾을 수 없다.", "event_log_append": []}

    def run_investigate(self, action: str, turn: int) -> dict[str, Any]:
        if self.event_engine:
            return self.event_engine.investigate(self.state, action, turn)
        return {
            "summary": "조사했지만 특별한 단서는 없었다.",
            "event_log_append": [{"turn": turn, "type": "investigate", "summary": "조사 — 없음"}],
        }

    def run_quest_status(self) -> dict[str, Any]:
        if self.event_engine:
            text = self.event_engine.show_quest_status(self.state)
        else:
            text = "퀘스트 시스템 없음"
        return {"summary": text, "lines": [text], "event_log_append": []}

    def run_rest(self, turn: int, loader: Any) -> dict[str, Any]:
        if self.event_engine:
            triggered = self.event_engine.try_trigger_event(self.state, "rest", turn)
            if triggered:
                triggered.setdefault("lines", [triggered["summary"]])
                # still heal after rest event
                self._heal_party(loader)
                return triggered

        self._heal_party(loader)
        zone = self.event_engine._location_zone(self.state) if self.event_engine else "ashpoint"
        if zone == "forest":
            summary = "숲 한구석에서 잠깐 눈을 붙였다. 새 소리가 멎어 있어 불안하다."
        elif zone == "tower":
            summary = "관측탑 벽에 기대어 숨을 고른다. 룬이 희미하게 진동한다."
        else:
            summary = "릴리안의 여관에서 휴식 — HP와 마나를 회복했다."
        return {
            "summary": summary,
            "lines": [summary],
            "event_log_append": [{"turn": turn, "type": "rest", "summary": summary}],
        }

    def _heal_party(self, loader: Any) -> None:
        for cid in self.state.get("party", []):
            char = loader.load_character(cid)
            char["stats"]["hp"] = char["stats"]["max_hp"]
            char["stats"]["mana"] = char["stats"]["max_mana"]
            loader.apply_character_updates(self.state, {cid: {"stats": char["stats"]}})
