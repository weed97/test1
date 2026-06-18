"""Event seeds, reputation, and quest progression — driven by rules + lore files."""

from __future__ import annotations

import random
import re
from typing import Any

from utils.content_loader import ContentLoader
from utils.faction_engine import FactionEngine
from utils.main_story_engine import MainStoryEngine
from utils.world_tension import adjust_tension, event_weight_multiplier, get_tension

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

FRONTIER_ZONES = frozenset({"ashpoint", "forest", "tower"})


def _seed_location_zones(seed: dict[str, Any]) -> frozenset[str]:
    explicit = seed.get("location_zones")
    if explicit:
        return frozenset(explicit)
    if seed.get("seed_type") == "main_story" or seed.get("main_plot_link"):
        return FRONTIER_ZONES
    return frozenset({"ashpoint"})


FOREST_ACT2_SEEDS = (
    "broken_rune_pillar",
    "tower_whisper",
    "mold_in_moss",
    "seal_drip",
    "sentinel_stirring",
)


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
        self.factions = FactionEngine(content.base_dir)
        self.main_story = MainStoryEngine(content.base_dir)

    def _location_zone(self, state: dict[str, Any]) -> str:
        from utils.spatial import resolve_zone_from_world

        return resolve_zone_from_world(state.get("world", {}))

    def _side_quests(self, state: dict[str, Any]) -> dict[str, Any]:
        return state.setdefault("flags", {}).setdefault("side_quests", {})

    def _activate_forest_act2_seeds(self, state: dict[str, Any]) -> None:
        pending = state.setdefault("flags", {}).setdefault("pending_events", [])
        triggered = set(state.get("flags", {}).get("triggered_events", []))
        for sid in FOREST_ACT2_SEEDS:
            if sid not in pending and sid not in triggered:
                pending.append(sid)

    def _start_torren_side_quest(self, state: dict[str, Any]) -> None:
        sq = self._side_quests(state)
        if sq.get("torren_lost_mold", {}).get("status") != "done":
            sq["torren_lost_mold"] = {"status": "active", "stage": 2}

    def _complete_side_quest(self, state: dict[str, Any], quest_id: str) -> str | None:
        catalog = self.content.load_quests()
        quest = catalog.get(quest_id)
        if not quest:
            return None
        sq = self._side_quests(state)
        sq[quest_id] = {"status": "done", "stage": len(quest.get("stages", [])) + 1}
        rewards = quest.get("rewards", {})
        outcome: dict[str, Any] = {"summary": quest.get("complete_summary", "사이드 퀘스트 완료")}
        for key in ("gold_delta", "tension_delta", "reputation", "flags_set", "rumor_add"):
            if key in rewards:
                outcome[key] = rewards[key]
        self._apply_outcome(state, outcome)
        return quest.get("complete_summary", "사이드 퀘스트 완료")

    def _reputation(self, state: dict[str, Any]) -> dict[str, int]:
        self.factions.ensure_initialized(state)
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
        adjust_tension(state, delta)

    def _apply_outcome(self, state: dict[str, Any], outcome: dict[str, Any], *, turn: int | None = None) -> list[str]:
        lines: list[str] = []
        if "tension_delta" in outcome:
            self._adjust_tension(state, int(outcome["tension_delta"]))
        if "gold_delta" in outcome or "currency_delta" in outcome:
            from utils.currency import grant

            delta = outcome.get("currency_delta") or {}
            if not delta and "gold_delta" in outcome:
                raw = int(outcome["gold_delta"])
                if abs(raw) >= 100:
                    delta = {"gold": raw}
                elif abs(raw) >= 5:
                    delta = {"silver": max(1, abs(raw) // 10) * (1 if raw > 0 else -1)}
                else:
                    delta = {"copper": raw}
            copper = int(delta.get("copper", 0))
            silver = int(delta.get("silver", 0))
            gold = int(delta.get("gold", 0))
            if copper or silver or gold:
                grant(
                    state,
                    copper=max(0, copper),
                    silver=max(0, silver),
                    gold=max(0, gold),
                    base_dir=self.content.base_dir,
                )
                parts = []
                if copper:
                    parts.append(f"{copper:+d}쿠퍼")
                if silver:
                    parts.append(f"{silver:+d}실버")
                if gold:
                    parts.append(f"{gold:+d}골드")
                lines.append("화폐 " + ", ".join(parts))
        lines.extend(self.factions.apply_reputation_outcome(state, outcome))
        lines.extend(self.main_story.on_outcome(state, outcome, turn=turn))
        for flag, val in (outcome.get("flags_set") or {}).items():
            state.setdefault("flags", {})[flag] = val
            lines.extend(self.main_story.on_flag_set(state, flag, turn=turn))
            if flag == "torren_side_quest" and val:
                self._start_torren_side_quest(state)
            if flag == "torren_mold_found" and val:
                sq = self._side_quests(state)
                if sq.get("torren_lost_mold", {}).get("status") == "active":
                    sq["torren_lost_mold"]["stage"] = 3
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

    def _eligible_seeds(
        self,
        state: dict[str, Any],
        action_kind: str,
        *,
        related_npc: str | None = None,
    ) -> list[dict[str, Any]]:
        pending = state.get("flags", {}).get("pending_events", [])
        if not pending:
            return []
        catalog = self.content.load_event_seeds()
        time_tags = _current_time_tags(state.get("world", {}).get("time_of_day", ""))
        zone = self._location_zone(state)
        flags = state.get("flags", {})
        quests = flags.get("quests", {})
        quest_stage = int(quests.get("stage", 1))
        active_quest = quests.get("active")
        tension = get_tension(state)
        self.factions.ensure_initialized(state)

        eligible: list[dict[str, Any]] = []
        for sid in pending:
            seed = catalog.get(sid)
            if not seed:
                continue
            seed_npc = seed.get("related_npc")
            if seed_npc:
                if not related_npc or seed_npc != related_npc:
                    continue
            elif related_npc:
                acts = set(seed.get("requires_action", ["explore"]))
                if "talk" in acts and "explore" in acts and seed.get("seed_type") != "main_story":
                    continue
            req_time = seed.get("requires_time")
            if req_time and not (time_tags & set(req_time)):
                continue
            req_action = seed.get("requires_action", ["explore"])
            if action_kind not in req_action and "any" not in req_action:
                continue
            if zone not in _seed_location_zones(seed):
                continue
            min_stage = seed.get("requires_quest_stage_min")
            if min_stage is not None:
                if active_quest != "smoke_on_the_mountain" or quest_stage < int(min_stage):
                    continue
            min_tension = seed.get("requires_tension_min")
            if min_tension is not None and tension < int(min_tension):
                continue
            max_tension = seed.get("requires_tension_max")
            if max_tension is not None and tension > int(max_tension):
                continue
            if not self.factions.meets_faction_requirements(
                state,
                seed.get("requires_faction_min"),
                seed.get("requires_faction_max"),
            ):
                continue
            if not self.main_story.meets_story_requirements(state, seed):
                continue
            if any(not flags.get(f) for f in seed.get("requires_flags", [])):
                continue
            if any(flags.get(f) for f in seed.get("requires_not_flags", [])):
                continue
            eligible.append(seed)
        return eligible

    def try_trigger_event(
        self,
        state: dict[str, Any],
        action_kind: str,
        turn: int,
        *,
        related_npc: str | None = None,
    ) -> dict[str, Any] | None:
        eligible = self._eligible_seeds(state, action_kind, related_npc=related_npc)
        if not eligible:
            return None
        weights = [
            max(1, int(s.get("weight", 10) * event_weight_multiplier(state, s)))
            for s in eligible
        ]
        seed = self.rng.choices(eligible, weights=weights, k=1)[0]
        outcome = seed.get("outcome", {})
        summary = outcome.get("summary", seed.get("summary", seed["title"]))
        extra_lines = self._apply_outcome(state, outcome, turn=turn)
        extra_lines.extend(self.main_story.on_seed_triggered(state, seed))
        self._consume_seed(state, seed["id"])
        self._maybe_advance_quest(state, seed)

        narrative = [str(line) for line in (outcome.get("lines") or []) if line]
        lines = [summary, *narrative, *extra_lines]
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
            self.main_story.on_quest_stage(state, active, quests["stage"] - 1)
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
            triggered = self.try_trigger_event(state, "talk", turn)
            if triggered:
                return triggered
            return {
                "summary": "누구와 이야기할지 unclear. 예: talk torren, talk 릴리안",
                "event_log_append": [],
            }

        char = loader.load_character(npc_id)
        rep = self._reputation(state)
        npc_rep_key = npc_id.split("_")[0] if npc_id != "grey_cloak" else "grey_cloak"
        rep[npc_rep_key] = rep.get(npc_rep_key, 0) + 2

        triggered = self.try_trigger_event(state, "talk", turn, related_npc=npc_id)
        if triggered:
            return triggered

        dialogues = self.content.load_npc_dialogues(npc_id, state)
        line = self.rng.choice(dialogues) if dialogues else f"{char['name']}이(가) 짧게 고개를 끄덕인다."

        attitude = self._npc_faction_attitude(state, npc_id)
        outcome_lines = [f"{char['name']}: \"{line}\""]
        if attitude:
            outcome_lines.append(attitude)
        quest_update = self._quest_talk_progress(state, npc_id)
        if quest_update:
            outcome_lines.append(quest_update)

        flags = state.setdefault("flags", {})
        if (
            npc_id == "torren_blacksmith"
            and flags.get("torren_mold_found")
            and not flags.get("torren_side_quest_done")
        ):
            done_msg = self._complete_side_quest(state, "torren_lost_mold")
            if done_msg:
                outcome_lines.append(f"[사이드 퀘스트] {done_msg}")

        if npc_id == "grey_cloak" and state.get("world", {}).get("tension", 0) >= 40:
            flags["grey_cloak_met"] = True
            outcome_lines.append("회색 망토가 작은 지도 조각을 슬쩍 보여준다.")

        summary = f"{char['name']}와(과) 대화했다."
        return {
            "summary": summary,
            "lines": outcome_lines,
            "event_log_append": [{"turn": turn, "type": "talk", "summary": summary, "npc": npc_id}],
        }

    def _npc_faction_attitude(self, state: dict[str, Any], npc_id: str) -> str | None:
        npc_factions = {
            "lilian_innkeeper": "silverwood_trade_union",
            "merchant_finn": "silverwood_trade_union",
            "elder_maren": "ashpoint_council",
            "grey_cloak": "ashen_wardens",
            "torren_blacksmith": "ashpoint_council",
        }
        fid = npc_factions.get(npc_id)
        if not fid:
            return None
        label = self.factions.attitude_label(state, fid)
        tier = self.factions.tier_id(state, fid)
        if tier in ("hostile", "allied"):
            name = (self.factions.faction_def(fid) or {}).get("name_ko", fid)
            return f"({name} 태도: {label})"
        return None

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
            self.main_story.record_mountain_visit(state, found=bool(state.get("flags", {}).get("tower_sighted")))
            quests = self._quests(state)
            if quests.get("active") == "smoke_on_the_mountain" and quests.get("stage") == 2:
                quests["stage"] = 3
                state.setdefault("world", {})["location"] = "북쪽 숲 — 연기가 보이는 외곽"
                self._adjust_tension(state, 8)
                self._activate_forest_act2_seeds(state)
                summary = "숲 속에서 검은 연기와 부서진 석탑 흔적을 발견했다. 무언가가 깨어나고 있다."
                return self._mechanical(
                    summary,
                    turn,
                    "investigate",
                    extra_lines=[
                        "[퀘스트] 3단계: 옛 관측탑 조사 (investigate tower / combat rune_sentinel)",
                        "[숲] 새로운 이벤트 씨앗이 활성화되었다.",
                    ],
                )

        if "tower" in lower or "관측" in lower or "석탑" in lower:
            self.main_story.record_mountain_visit(state, found=True)
            quests = self._quests(state)
            if quests.get("active") == "smoke_on_the_mountain" and int(quests.get("stage", 1)) >= 3:
                state.setdefault("world", {})["location"] = "옛 관측탑 — 입구"
                triggered = self.try_trigger_event(state, "investigate", turn)
                if triggered:
                    return triggered
                summary = "관측탑 입구. 석재 사이로 차가운 바람이 새어 나온다. explore로 더 깊이 들어가거나, combat rune_sentinel."
                return self._mechanical(summary, turn, "investigate")

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
        lines: list[str] = []
        quests = self._quests(state)
        active = quests.get("active")
        if active:
            catalog = self.content.load_quests()
            quest = catalog.get(active)
            if quest:
                stage = int(quests.get("stage", 1))
                stages = quest.get("stages", [])
                if stage <= len(stages):
                    s = stages[stage - 1]
                    hint = s.get("hint", "")
                    lines.append(f"{quest['title']} — {stage}/{len(stages)}: {s['goal']}")
                    if hint:
                        lines.append(f"  힌트: {hint}")
                else:
                    lines.append(f"{quest['title']} — 완료 대기")
            else:
                lines.append(f"퀘스트 {active}")
        else:
            lines.append("진행 중인 메인 퀘스트 없음")

        sq = self._side_quests(state)
        torren = sq.get("torren_lost_mold", {})
        if torren.get("status") == "active":
            catalog = self.content.load_quests()
            side = catalog.get("torren_lost_mold", {})
            st = int(torren.get("stage", 1))
            stages = side.get("stages", [])
            if st <= len(stages):
                lines.append(f"[사이드] {side.get('title', '토렌')} — {stages[st - 1]['goal']}")
        ms_line = self.main_story.format_summary(state)
        if ms_line:
            lines.append(f"[장기] {ms_line}")
        return "\n".join(lines) if lines else "진행 중인 퀘스트 없음"
