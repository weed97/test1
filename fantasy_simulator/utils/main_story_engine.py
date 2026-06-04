"""Long-term main story — phases, branching choices, ending tracker."""

from __future__ import annotations

from typing import Any

from utils.io_helpers import load_json
from utils.world_tension import adjust_tension, get_tension


class MainStoryEngine:
    def __init__(self, base_dir: Any) -> None:
        from pathlib import Path

        self.base_dir = Path(base_dir)
        self._catalog: dict[str, Any] | None = None

    def load_catalog(self) -> dict[str, Any]:
        if self._catalog is None:
            path = self.base_dir / "events" / "main_stories.json"
            self._catalog = load_json(path) if path.exists() else {"stories": []}
        return self._catalog

    def _resolve_story_id(self, story_id: str) -> str:
        return self.load_catalog().get("legacy_story_ids", {}).get(story_id, story_id)

    def story_def(self, story_id: str) -> dict[str, Any] | None:
        resolved = self._resolve_story_id(story_id)
        for story in self.load_catalog().get("stories", []):
            if story["id"] == resolved:
                return story
        return None

    def ensure_initialized(self, state: dict[str, Any], *, turn: int = 0) -> dict[str, Any]:
        flags = state.setdefault("flags", {})
        ms = flags.setdefault("main_story", {})
        self._migrate_story_state(ms)

        if not ms.get("id"):
            catalog = self.load_catalog()
            active_quest = flags.get("quests", {}).get("active")
            chosen = catalog.get("default_story", "ashen_seal_cracking")
            for story in catalog.get("stories", []):
                if story.get("linked_quest") == active_quest:
                    chosen = story["id"]
                    break
            ms.update(
                {
                    "id": chosen,
                    "phase": 1,
                    "progress": 0,
                    "started_turn": turn,
                    "choices_made": [],
                    "ending_scores": {},
                    "leading_ending": None,
                    "rumor_tone": "uncertain",
                    "resolved_ending": None,
                    "phase1_step": 0,
                    "factions_contacted": [],
                }
            )

        ms.setdefault("phase", ms.pop("stage", 1))
        ms.setdefault("progress", 0)
        ms.setdefault("choices_made", [])
        ms.setdefault("ending_scores", {})
        ms.setdefault("rumor_tone", "uncertain")
        ms.setdefault("phase1_step", 0)
        ms.setdefault("factions_contacted", [])
        return ms

    def _migrate_story_state(self, ms: dict[str, Any]) -> None:
        catalog = self.load_catalog()
        legacy = catalog.get("legacy_story_ids", {})
        old_id = ms.get("id")
        if old_id in legacy:
            ms["id"] = legacy[old_id]
        if "stage" in ms and "phase" not in ms:
            ms["phase"] = ms.pop("stage")

    def current(self, state: dict[str, Any]) -> dict[str, Any]:
        return self.ensure_initialized(state)

    def get_phase(self, state: dict[str, Any]) -> int:
        return int(self.ensure_initialized(state).get("phase", 1))

    def add_progress(self, state: dict[str, Any], amount: int, *, reason: str | None = None) -> list[str]:
        ms = self.ensure_initialized(state)
        story = self.story_def(ms["id"])
        if not story or ms.get("resolved_ending"):
            return []
        before = int(ms.get("progress", 0))
        ms["progress"] = min(100, before + int(amount))
        lines: list[str] = []
        if amount and reason:
            lines.append(f"[메인 스토리] {story['title']} +{amount} ({reason})")

        self._maybe_advance_phase(state, story, ms)
        self._maybe_queue_phase_events(state, story, ms, before)
        self._recalculate_ending_scores(state, story, ms)
        lines.extend(self._check_phase1_exit(state, story, ms))
        if int(ms.get("progress", 0)) >= 100 and not ms.get("resolved_ending"):
            lines.extend(self._try_resolve_ending(state, story, ms))
        return lines

    def _phase_def(self, story: dict[str, Any], phase: int) -> dict[str, Any] | None:
        for p in story.get("phases", []):
            if int(p.get("phase", 0)) == phase:
                return p
        return None

    def _maybe_advance_phase(self, state: dict[str, Any], story: dict[str, Any], ms: dict[str, Any]) -> None:
        phases = story.get("phases", [])
        phase_idx = int(ms.get("phase", 1)) - 1
        if phase_idx >= len(phases):
            return
        needed = int(phases[phase_idx].get("progress_needed", 100))
        if int(ms.get("progress", 0)) >= needed and phase_idx + 1 < len(phases):
            ms["phase"] = phase_idx + 2
            next_phase = phases[phase_idx + 1]
            state.setdefault("flags", {})["main_story_phase_bump"] = next_phase.get("name", "")

    def _maybe_queue_phase_events(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
        progress_before: int,
    ) -> None:
        phase_events = story.get("phase_events", {})
        phase_key = str(int(ms.get("phase", 1)))
        spec = phase_events.get(phase_key)
        if not spec:
            return
        threshold = int(spec.get("at_progress", 0))
        progress = int(ms.get("progress", 0))
        if progress_before < threshold <= progress:
            pending = state.setdefault("flags", {}).setdefault("pending_events", [])
            for event_id in spec.get("pending", []):
                if event_id not in pending:
                    pending.append(event_id)

    def _resolve_choice_id(self, story: dict[str, Any], choice_id: str) -> str:
        return story.get("legacy_choice_ids", {}).get(choice_id, choice_id)

    def _find_choice(self, story: dict[str, Any], choice_id: str) -> dict[str, Any] | None:
        choice_id = self._resolve_choice_id(story, choice_id)
        for pool in ("phase1_choices", "phase2_choices"):
            for choice in story.get(pool, []):
                if choice["id"] == choice_id:
                    return choice
        return None

    def apply_choice(self, state: dict[str, Any], choice_id: str) -> list[str]:
        ms = self.ensure_initialized(state)
        story = self.story_def(ms["id"])
        if not story or ms.get("resolved_ending"):
            return []
        choice_id = self._resolve_choice_id(story, choice_id)
        choice = self._find_choice(story, choice_id)
        if not choice:
            return []

        choices_made: list[str] = ms.setdefault("choices_made", [])
        if choice_id in choices_made:
            return []

        lines: list[str] = [f"[메인 선택] {choice.get('label', choice_id)}"]
        choices_made.append(choice_id)

        flags = state.setdefault("flags", {})
        for flag, val in (choice.get("flags_set") or {}).items():
            flags[flag] = val

        tone = choice.get("rumor_tone")
        if tone:
            ms["rumor_tone"] = tone
            rumors = state.setdefault("world", {}).setdefault("rumors", [])
            rumor_text = self._rumor_for_tone(tone, story)
            if rumor_text and rumor_text not in rumors:
                rumors.append(rumor_text)
                lines.append(f"[소문] {rumor_text}")

        if "tension_delta" in choice:
            adjust_tension(state, int(choice["tension_delta"]))

        from utils.faction_engine import FactionEngine

        faction_engine = FactionEngine(self.base_dir)
        outcome = {
            "faction_reputation": choice.get("faction_reputation", {}),
        }
        lines.extend(faction_engine.apply_reputation_outcome(state, outcome))

        self._remove_blocked_choice_events(state, story, choice)
        self._recalculate_ending_scores(state, story, ms)
        if int(ms.get("phase", 1)) == 1:
            self._advance_phase1_from_flag(state, story, ms, "story_phase1_chosen")
            lines.extend(self._queue_phase1_step_events(state, story, ms, 5))
            amount = story.get("progress_sources", {}).get("flags", {}).get("story_phase1_chosen")
            if amount and "story_phase1_chosen" in (choice.get("flags_set") or {}):
                lines.extend(self.add_progress(state, int(amount), reason="1단계 분기"))
            else:
                lines.extend(self._check_phase1_exit(state, story, ms))

        summary = choice.get("summary")
        if summary:
            lines.append(summary)
        return lines

    def _choice_seed_map(self) -> dict[str, str]:
        return {
            "ally_village": "story_choice_council",
            "seek_truth": "story_choice_warden",
            "pursue_power": "story_choice_covenant",
            "exploit_chaos": "story_choice_opportunist",
            "stay_neutral": "story_choice_stay_neutral",
            "path_alliance": "story_choice_alliance",
            "path_neutral": "story_choice_neutral",
            "path_betrayal": "story_choice_betrayal",
        }

    def _remove_blocked_choice_events(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        choice: dict[str, Any],
    ) -> None:
        blocked = choice.get("blocks_choices", [])
        if not blocked:
            return
        pending = state.get("flags", {}).get("pending_events", [])
        seed_map = self._choice_seed_map()
        legacy = story.get("legacy_choice_ids", {})
        for cid in blocked:
            resolved = legacy.get(cid, cid)
            sid = seed_map.get(resolved)
            if sid and sid in pending:
                pending.remove(sid)

    def _rumor_for_tone(self, tone: str, story: dict[str, Any]) -> str:
        rumors = {
            "reassurance": "마을 장로는 산의 연기가 곧 잦아들 것이라 말한다.",
            "mystery": "회색 망토를 본 사람들은 봉인 이야기를 입 밖에 내지 않는다.",
            "fear": "밤마다 우물에서 이상한 속삭임이 들린다는 소문이 퍼진다.",
            "uncertain": "검은 연기의 정체를 아는 이는 없다.",
        }
        return rumors.get(tone, f"{story.get('title', '봉인')} 관련 소문이 바뀌고 있다.")

    def _phase1_flow(self, story: dict[str, Any]) -> dict[str, Any]:
        return story.get("phase1_flow", {})

    def _advance_phase1_from_flag(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
        flag: str,
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 1:
            return []
        flow = self._phase1_flow(story)
        flags_to_step = flow.get("flags_to_step", {})
        step = flags_to_step.get(flag)
        if step is None:
            return []
        lines: list[str] = []
        current = int(ms.get("phase1_step", 0))
        if int(step) > current:
            ms["phase1_step"] = int(step)
            lines.extend(self._queue_phase1_step_events(state, story, ms, int(step)))
        if flag == "phase1_rumors_spread" and not state.get("flags", {}).get("phase1_factions_active"):
            state.setdefault("flags", {})["phase1_factions_active"] = True
            if int(ms.get("phase1_step", 0)) < 3:
                ms["phase1_step"] = 3
                lines.extend(self._queue_phase1_step_events(state, story, ms, 3))
        return lines

    def _queue_phase1_step_events(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
        step: int,
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 1:
            return []
        flow = self._phase1_flow(story)
        step_queue = flow.get("step_queue", {})
        events = step_queue.get(str(step), [])
        if step == 4:
            min_contacts = int(flow.get("branch_queue_min_contacts", 1))
            if len(ms.get("factions_contacted", [])) < min_contacts:
                return []
        pending = state.setdefault("flags", {}).setdefault("pending_events", [])
        added: list[str] = []
        for event_id in events:
            if event_id not in pending:
                pending.append(event_id)
                added.append(event_id)
        if added and step == 4:
            return ["[1단계] 세력 접촉 후 첫 분기점이 열렸다."]
        return []

    def record_faction_contact(self, state: dict[str, Any], faction_id: str) -> list[str]:
        ms = self.ensure_initialized(state)
        story = self.story_def(ms["id"])
        if not story or int(ms.get("phase", 1)) != 1:
            return []
        contacted: list[str] = ms.setdefault("factions_contacted", [])
        if faction_id in contacted:
            return []
        contacted.append(faction_id)
        lines: list[str] = [f"[1단계] {faction_id} 세력과 접촉"]
        flow = self._phase1_flow(story)
        min_contacts = int(flow.get("branch_queue_min_contacts", 1))
        if len(contacted) >= min_contacts and int(ms.get("phase1_step", 0)) >= 2:
            if int(ms.get("phase1_step", 0)) < 4 and not state.get("flags", {}).get("story_phase1_chosen"):
                ms["phase1_step"] = max(int(ms.get("phase1_step", 0)), 3)
                lines.extend(self._queue_phase1_step_events(state, story, ms, 4))
        return lines

    def _check_phase1_exit(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 1 or ms.get("phase1_complete"):
            return []
        exit_cfg = story.get("phase1_exit")
        if not exit_cfg:
            return []
        if int(ms.get("progress", 0)) < int(exit_cfg.get("min_progress", 0)):
            return []
        flags = state.get("flags", {})
        faction_rep = flags.get("faction_reputation", {})
        for rule in exit_cfg.get("any_of", []):
            if rule.get("flag") and flags.get(rule["flag"]):
                return self._complete_phase1(state, story, ms, rule["flag"])
            if rule.get("faction_rep_min") is not None:
                threshold = int(rule["faction_rep_min"])
                if any(int(v) >= threshold for v in faction_rep.values()):
                    return self._complete_phase1(state, story, ms, "faction_alliance")
            if rule.get("tension_min") is not None and get_tension(state) >= int(rule["tension_min"]):
                return self._complete_phase1(state, story, ms, "tension")
            req_flag = rule.get("requires_flag")
            if rule.get("factions_contacted_min") is not None:
                minimum = int(rule["factions_contacted_min"])
                if len(ms.get("factions_contacted", [])) >= minimum and (not req_flag or flags.get(req_flag)):
                    return self._complete_phase1(state, story, ms, "multi_contact")
        return []

    def _complete_phase1(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
        reason: str,
    ) -> list[str]:
        ms["phase1_complete"] = True
        phases = story.get("phases", [])
        phase1_needed = int(phases[0].get("progress_needed", 35)) if phases else 35
        if int(ms.get("progress", 0)) < phase1_needed:
            ms["progress"] = phase1_needed
        if int(ms.get("phase", 1)) == 1:
            ms["phase"] = 2
            next_name = phases[1]["name"] if len(phases) > 1 else "2단계"
            state.setdefault("flags", {})["main_story_phase_bump"] = next_name
        self._maybe_queue_phase_events(state, story, ms, phase1_needed - 1)
        return [f"[1단계 완료] 균열의 전조 — {reason}"]

    def _phase1_step_label(self, story: dict[str, Any], step: int) -> str:
        labels = {
            0: "대기",
            1: "검은 연기 목격",
            2: "소문 확산",
            3: "세력 접촉",
            4: "첫 분기",
            5: "1단계 클라이맥스",
        }
        return labels.get(step, f"단계 {step}")

    def _recalculate_ending_scores(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
    ) -> None:
        weights = story.get("ending_weights", {})
        scores: dict[str, float] = {eid: 0.0 for eid in weights}
        faction_rep = state.get("flags", {}).get("faction_reputation", {})
        choices_made = set(ms.get("choices_made", []))

        for ending_id, spec in weights.items():
            score = 0.0
            for fid, mult in (spec.get("faction") or {}).items():
                score += int(faction_rep.get(fid, 0)) * float(mult)
            for cid, pts in (spec.get("choices") or {}).items():
                if cid in choices_made:
                    score += float(pts)
            for cid, pts in (spec.get("anti_choices") or {}).items():
                if cid in choices_made:
                    score += float(pts)
            if spec.get("requires_flags") and not all(state.get("flags", {}).get(f) for f in spec["requires_flags"]):
                score *= 0.25
            tension_min = spec.get("tension_min")
            if tension_min is not None and get_tension(state) < int(tension_min):
                score *= 0.5
            spread_min = spec.get("faction_spread_min")
            if spread_min is not None:
                non_zero = sum(1 for v in faction_rep.values() if abs(int(v)) >= 10)
                if non_zero >= int(spread_min):
                    score += 10
            scores[ending_id] = round(score, 1)

        for cid in choices_made:
            choice = self._find_choice(story, cid)
            if not choice:
                continue
            for eid, pts in (choice.get("ending_bias") or {}).items():
                scores[eid] = round(scores.get(eid, 0) + float(pts), 1)

        ms["ending_scores"] = scores
        ms["leading_ending"] = self._pick_leading_ending(story, scores)

    def _pick_leading_ending(self, story: dict[str, Any], scores: dict[str, float]) -> str | None:
        if not scores:
            return None
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if ranked[0][1] <= 0:
            return None
        return ranked[0][0]

    def _try_resolve_ending(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
    ) -> list[str]:
        self._recalculate_ending_scores(state, story, ms)
        ending_id = ms.get("leading_ending")
        if not ending_id:
            ending_id = "age_of_chaos"
        ending = next((e for e in story.get("endings", []) if e["id"] == ending_id), None)
        if not ending:
            return []
        ms["resolved_ending"] = ending_id
        ms["phase"] = len(story.get("phases", []))

        flags = state.setdefault("flags", {})
        for flag, val in (ending.get("flags_set") or {}).items():
            flags[flag] = val
        if "tension_delta" in ending:
            adjust_tension(state, int(ending["tension_delta"]))

        return [
            f"[결말] {ending['title']}",
            ending.get("summary", ""),
            f"세계 변화: {ending.get('world_change', '')}",
        ]

    def on_seed_triggered(self, state: dict[str, Any], seed: dict[str, Any]) -> list[str]:
        ms = self.ensure_initialized(state)
        story = self.story_def(ms["id"])
        if not story:
            return []
        sources = story.get("progress_sources", {})
        seed_map = sources.get("seed_ids", {})
        amount = seed_map.get(seed.get("id"))
        if not amount:
            return []
        return self.add_progress(state, int(amount), reason=seed.get("title", seed.get("id")))

    def on_quest_stage(self, state: dict[str, Any], quest_id: str, stage: int) -> list[str]:
        ms = self.ensure_initialized(state)
        story = self.story_def(ms["id"])
        if not story or story.get("linked_quest") != quest_id:
            return []
        sources = story.get("progress_sources", {})
        stage_deltas = sources.get("quest_stage", {}).get(quest_id, [])
        if stage <= 0 or stage > len(stage_deltas):
            return []
        return self.add_progress(state, int(stage_deltas[stage - 1]), reason=f"퀘스트 {stage}단계")

    def on_flag_set(self, state: dict[str, Any], flag: str) -> list[str]:
        ms = self.ensure_initialized(state)
        story = self.story_def(ms["id"])
        if not story:
            return []
        lines: list[str] = []
        lines.extend(self._advance_phase1_from_flag(state, story, ms, flag))
        amount = story.get("progress_sources", {}).get("flags", {}).get(flag)
        if amount:
            lines.extend(self.add_progress(state, int(amount), reason=flag))
        else:
            lines.extend(self._check_phase1_exit(state, story, ms))
        return lines

    def on_outcome(self, state: dict[str, Any], outcome: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        choice_id = outcome.get("main_story_choice")
        if choice_id:
            lines.extend(self.apply_choice(state, choice_id))
        faction_id = outcome.get("main_story_faction_contact")
        if faction_id:
            lines.extend(self.record_faction_contact(state, faction_id))
        p1_flag = outcome.get("main_story_phase1_flag")
        if p1_flag:
            ms = self.ensure_initialized(state)
            story = self.story_def(ms["id"])
            if story:
                lines.extend(self._advance_phase1_from_flag(state, story, ms, p1_flag))
        return lines

    def tick(self, state: dict[str, Any], *, turn: int) -> list[str]:
        ms = self.ensure_initialized(state, turn=turn)
        story = self.story_def(ms["id"])
        if not story or ms.get("resolved_ending"):
            return []
        lines: list[str] = []
        sources = story.get("progress_sources", {})

        if get_tension(state) >= 50 and turn % 6 == 0:
            lines.extend(self.add_progress(state, 1, reason="봉인 균열"))

        bump = state.get("flags", {}).pop("main_story_phase_bump", None)
        if bump:
            lines.append(f"[메인 스토리] {story['title']} — {bump}")

        self._recalculate_ending_scores(state, story, ms)
        lines.extend(self._check_phase1_exit(state, story, ms))
        leading = ms.get("leading_ending")
        if leading and turn % 10 == 0:
            ending = next((e for e in story.get("endings", []) if e["id"] == leading), None)
            if ending:
                lines.append(f"[결말 징후] {ending['title']} 쪽으로 기울어짐")

        return lines

    def format_summary(self, state: dict[str, Any]) -> str:
        ms = self.ensure_initialized(state)
        story = self.story_def(ms["id"])
        if not story:
            return "메인 스토리: (미설정)"
        phase = int(ms.get("phase", 1))
        phases = story.get("phases", [])
        phase_def = self._phase_def(story, phase)
        goal = phase_def["goal"] if phase_def else "막바지"
        phase_name = phase_def["name"] if phase_def else f"{phase}단계"

        parts = [
            f"{story['title']} — {phase_name} ({phase}/{len(phases)})",
            f"진행 {ms.get('progress', 0)}/100 | {goal}",
        ]
        if phase == 1:
            step = int(ms.get("phase1_step", 0))
            contacts = len(ms.get("factions_contacted", []))
            parts.append(
                f"1단계 흐름: {self._phase1_step_label(story, step)} | 세력 접촉 {contacts}"
            )
        if ms.get("resolved_ending"):
            ending = next((e for e in story.get("endings", []) if e["id"] == ms["resolved_ending"]), None)
            if ending:
                parts.append(f"결말: {ending['title']}")
        elif ms.get("leading_ending"):
            ending = next((e for e in story.get("endings", []) if e["id"] == ms["leading_ending"]), None)
            if ending:
                parts.append(f"결말 징후: {ending['title']}")
        tone = ms.get("rumor_tone")
        if tone and tone != "uncertain":
            parts.append(f"소문 분위기: {tone}")
        return " | ".join(parts)

    def ending_tracker_summary(self, state: dict[str, Any]) -> list[str]:
        ms = self.ensure_initialized(state)
        scores = ms.get("ending_scores", {})
        if not scores:
            return []
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        story = self.story_def(ms["id"])
        lines: list[str] = []
        for eid, score in ranked:
            if score <= 0:
                continue
            ending = next((e for e in (story or {}).get("endings", []) if e["id"] == eid), None)
            title = ending["title"] if ending else eid
            lines.append(f"  - {title}: {score}")
        return lines

    def select_story(self, state: dict[str, Any], story_id: str, *, turn: int = 0) -> bool:
        if not self.story_def(story_id):
            return False
        state.setdefault("flags", {})["main_story"] = {
            "id": story_id,
            "phase": 1,
            "progress": 0,
            "started_turn": turn,
            "choices_made": [],
            "ending_scores": {},
            "leading_ending": None,
            "rumor_tone": "uncertain",
            "resolved_ending": None,
            "phase1_step": 0,
            "factions_contacted": [],
        }
        return True

    def meets_story_requirements(self, state: dict[str, Any], seed: dict[str, Any]) -> bool:
        ms = self.ensure_initialized(state)
        req_phase = seed.get("requires_main_story_phase")
        if req_phase is not None and int(ms.get("phase", 1)) != int(req_phase):
            return False
        step_min = seed.get("requires_main_story_step_min")
        if step_min is not None and int(ms.get("phase1_step", 0)) < int(step_min):
            return False
        step_max = seed.get("requires_main_story_step_max")
        if step_max is not None and int(ms.get("phase1_step", 0)) > int(step_max):
            return False
        min_progress = seed.get("requires_main_story_min_progress")
        if min_progress is not None and int(ms.get("progress", 0)) < int(min_progress):
            return False
        req_choice = seed.get("requires_main_story_choice")
        if req_choice and req_choice not in ms.get("choices_made", []):
            return False
        not_choice = seed.get("requires_not_main_story_choice")
        if not_choice and not_choice in ms.get("choices_made", []):
            return False
        return True
