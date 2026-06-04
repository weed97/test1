"""Event seeds, reputation, and quest progression — driven by rules + lore files."""

from __future__ import annotations

import random
import re
from typing import Any

from utils.content_loader import ContentLoader

TIME_ALIASES: dict[str, list[str]] = {
    "morning": ["morning", "아침", "오전"],
    "afternoon": ["afternoon", "낮", "오후"],
    "evening": ["evening", "저녁"],
    "night": ["night", "밤", "한밤"],
}

NPC_ALIASES: dict[str, str] = {
    "torren": "torren_blacksmith",
    "토렌": "torren_blacksmith",
    "lilian": "lilian_innkeeper",
    "릴리안": "lilian_innkeeper",
    "grey_cloak": "grey_cloak",
    "grey": "grey_cloak",
    "회색": "grey_cloak",
    "망토": "grey_cloak",
    "maren": "elder_maren",
    "장로": "elder_maren",
    "lysa": "child_lysa",
    "아이": "child_lysa",
    "finn": "merchant_finn",
    "상인": "merchant_finn",
}


def resolve_npc_id(text: str) -> str | None:
    lower = text.lower()
    for alias, nid in NPC_ALIASES.items():
        if alias in lower:
            return nid
    return None


def _current_time_tags(time_of_day: str) -> set[str]:
    tags: set[str] = set()
    for tag, aliases in TIME_ALIASES.items():
        if any(a in time_of_day for a in aliases):
            tags.add(tag)
    return tags or {time_of_day}


class EventEngine:
    def __init__(self, content: ContentLoader, rng: random.Random) -> None:
        self.content = content
        self.rng = rng

    def _reputation(self, state: dict[str, Any]) -> dict[str, int]:
        rep = state.setdefault("flags", {}).setdefault("reputation", {})
        rep.setdefault("ashpoint", 50)
        return rep

    def _quests(self, state: dict[str, Any]) -> dict[str, Any]:
        q = state.setdefault("flags", {}).setdefault("quests", {})
        q.setdefault("active", "smoke_on_the_mountain")
        q.setdefault("stage", 1)
        q.setdefault("completed", [])
        return q

    def _adjust_tension(self, state: dict[str, Any], delta: int) -> None:
        world = state.setdefault("world", {})
        t = int(world.get("tension", 42))
        world["tension"] = max(0, min(100, t + delta))

    def _apply_outcome(self, state: dict[str, Any], outcome: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        if "tension_delta" in outcome:
            self._adjust_tension(state, int(outcome["tension_delta"]))
        if "gold_delta" in outcome:
            inv = state.setdefault("inventory", {})
            inv["party_gold"] = inv.get("party_gold", 0) + int(outcome["gold_delta"])
            lines.append(f"골드 {outcome['gold_delta']:+d}")
        rep = self._reputation(state)
        for key, delta in (outcome.get("reputation") or {}).items():
            rep[key] = max(-100, min(100, rep.get(key, 0) + int(delta)))
        for flag, val in (outcome.get("flags_set") or {}).items():
            state.setdefault("flags", {})[flag] = val
        if outcome.get("rumor_add"):
            state.setdefault("world", {}).setdefault("rumors", []).append(outcome["rumor_add"])
        if outcome.get("location"):
            state.setdefault("world", {})["location"] = outcome["location"]
        return lines

    def _consume_seed(self, state: dict[str, Any], seed_id: str) -> None:
        pending = state.setdefault("flags", {}).setdefault("pending_events", [])
        if seed_id in pending:
            pending.remove(seed_id)
        triggered = state.setdefault("flags", {}).setdefault("triggered_events", [])
        if seed_id not in triggered:
            triggered.append(seed_id)

    def _eligible_seeds(self, state: dict[str, Any], action_kind: str) -> list[dict[str, Any]]:
        pending = state.get("flags", {}).get("pending_events", [])
        if not pending:
            return []
        catalog = self.content.load_event_seeds()
        time_tags = _current_time_tags(state.get("world", {}).get("time_of_day", ""))
        eligible: list[dict[str, Any]] = []
        for sid in pending:
            seed = catalog.get(sid)
            if not seed:
                continue
            req_time = seed.get("requires_time")
            if req_time and not (time_tags & set(req_time)):
                continue
            req_action = seed.get("requires_action", ["explore"])
            if action_kind not in req_action and "any" not in req_action:
                continue
            eligible.append(seed)
        return eligible

    def try_trigger_event(
        self,
        state: dict[str, Any],
        action_kind: str,
        turn: int,
    ) -> dict[str, Any] | None:
        eligible = self._eligible_seeds(state, action_kind)
        if not eligible:
            return None
        weights = [s.get("weight", 10) for s in eligible]
        seed = self.rng.choices(eligible, weights=weights, k=1)[0]
        outcome = seed.get("outcome", {})
        summary = outcome.get("summary", seed.get("summary", seed["title"]))
        extra_lines = self._apply_outcome(state, outcome)
        self._consume_seed(state, seed["id"])
        self._maybe_advance_quest(state, seed)

        lines = [summary, *extra_lines]
        return {
            "summary": summary,
            "lines": lines,
            "event_log_append": [{"turn": turn, "type": "event", "summary": summary, "seed_id": seed["id"]}],
            "seed_id": seed["id"],
            "seed_title": seed["title"],
        }

    def _maybe_advance_quest(self, state: dict[str, Any], seed: dict[str, Any]) -> None:
        quests = self._quests(state)
        active = quests.get("active")
        if not active:
            return
        catalog = self.content.load_quests()
        quest = catalog.get(active)
        if not quest:
            return
        stage = int(quests.get("stage", 1))
        stages = quest.get("stages", [])
        if stage > len(stages):
            return
        stage_def = stages[stage - 1]
        triggers = stage_def.get("triggers", [])
        if seed["id"] in triggers or seed.get("id") in stage_def.get("any_seed", []):
            quests["stage"] = stage + 1
            if quests["stage"] > len(stages):
                self._complete_quest(state, quest)

    def _complete_quest(self, state: dict[str, Any], quest: dict[str, Any]) -> None:
        quests = self._quests(state)
        qid = quest["id"]
        completed = quests.setdefault("completed", [])
        if qid not in completed:
            completed.append(qid)
        rewards = quest.get("rewards", {})
        outcome: dict[str, Any] = {"summary": quest.get("complete_summary", "퀘스트 완료")}
        for key in ("gold_delta", "tension_delta", "reputation", "flags_set", "rumor_add"):
            if key in rewards:
                outcome[key] = rewards[key]
        self._apply_outcome(state, outcome)
        quests["active"] = quest.get("next_quest")

    def talk(self, state: dict[str, Any], action: str, turn: int, loader: Any) -> dict[str, Any]:
        npc_id = resolve_npc_id(action)
        if not npc_id:
            return {
                "summary": "누구와 이야기할지 unclear. 예: talk torren, talk 릴리안",
                "event_log_append": [],
            }

        char = loader.load_character(npc_id)
        rep = self._reputation(state)
        npc_rep_key = npc_id.split("_")[0] if npc_id != "grey_cloak" else "grey_cloak"
        rep[npc_rep_key] = rep.get(npc_rep_key, 0) + 2

        dialogues = self.content.load_npc_dialogues(npc_id)
        line = self.rng.choice(dialogues) if dialogues else f"{char['name']}이(가) 짧게 고개를 끄덕인다."

        outcome_lines = [f"{char['name']}: \"{line}\""]
        quest_update = self._quest_talk_progress(state, npc_id)
        if quest_update:
            outcome_lines.append(quest_update)

        # Special: grey cloak at high tension
        if npc_id == "grey_cloak" and state.get("world", {}).get("tension", 0) >= 40:
            state.setdefault("flags", {})["grey_cloak_met"] = True
            outcome_lines.append("회색 망토가 작은 지도 조각을 슬쩍 보여준다.")

        summary = f"{char['name']}와(과) 대화했다."
        return {
            "summary": summary,
            "lines": outcome_lines,
            "event_log_append": [{"turn": turn, "type": "talk", "summary": summary, "npc": npc_id}],
        }

    def _quest_talk_progress(self, state: dict[str, Any], npc_id: str) -> str | None:
        flags = state.setdefault("flags", {})
        quests = flags.setdefault("quests", {})
        if quests.get("active") != "smoke_on_the_mountain" or int(quests.get("stage", 1)) != 1:
            return None
        talked: list[str] = flags.setdefault("quest_talked_npcs", [])
        if npc_id not in talked:
            talked.append(npc_id)
        needed = {"torren_blacksmith", "lilian_innkeeper", "grey_cloak"}
        if needed.issubset(set(talked)):
            quests["stage"] = 2
            return "[퀘스트] '산의 검은 연기' 2단계: 북쪽 숲 외곽 조사 (investigate forest)"
        return f"[퀘스트] 정보 수집 ({len(set(talked) & needed)}/{len(needed)})"

    def investigate(self, state: dict[str, Any], action: str, turn: int) -> dict[str, Any]:
        lower = action.lower()

        if "forest" in lower or "숲" in lower:
            quests = self._quests(state)
            if quests.get("active") == "smoke_on_the_mountain" and quests.get("stage") == 2:
                quests["stage"] = 3
                state.setdefault("world", {})["location"] = "북쪽 숲 — 연기가 보이는 외곽"
                self._adjust_tension(state, 8)
                summary = "숲 속에서 검은 연기와 부서진 석탑 흔적을 발견했다. 무언가가 깨어나고 있다."
                return self._mechanical(summary, turn, "investigate", extra_lines=["[퀘스트] 3단계: 연기의 근원에 접근"])

        if "well" in lower or "우물" in lower:
            self._adjust_tension(state, 5)
            summary = "우물가에 낡은 룬 문자가 새겨져 있다. 최근 누군가 지웠으나 흔적이 남아 있다."
            self._consume_seed_if_pending(state, "well_sound")
            return self._mechanical(summary, turn, "investigate")

        triggered = self.try_trigger_event(state, "investigate", turn)
        if triggered:
            return triggered

        return {
            "summary": "주변을 조사했지만 특별한 단서는 없었다.",
            "event_log_append": [{"turn": turn, "type": "investigate", "summary": "조사 — 특이사항 없음"}],
        }

    def _consume_seed_if_pending(self, state: dict[str, Any], seed_id: str) -> None:
        if seed_id in state.get("flags", {}).get("pending_events", []):
            self._consume_seed(state, seed_id)

    def _mechanical(
        self,
        summary: str,
        turn: int,
        kind: str,
        *,
        extra_lines: list[str] | None = None,
    ) -> dict[str, Any]:
        lines = [summary, *(extra_lines or [])]
        return {
            "summary": summary,
            "lines": lines,
            "event_log_append": [{"turn": turn, "type": kind, "summary": summary}],
        }

    def show_quest_status(self, state: dict[str, Any]) -> str:
        quests = self._quests(state)
        active = quests.get("active")
        if not active:
            return "진행 중인 퀘스트 없음"
        catalog = self.content.load_quests()
        quest = catalog.get(active)
        if not quest:
            return f"퀘스트 {active}"
        stage = int(quests.get("stage", 1))
        stages = quest.get("stages", [])
        if stage <= len(stages):
            s = stages[stage - 1]
            return f"{quest['title']} — {stage}/{len(stages)}: {s['goal']}"
        return f"{quest['title']} — 완료 대기"
