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
                }
            )

        ms.setdefault("phase", ms.pop("stage", 1))
        ms.setdefault("progress", 0)
        ms.setdefault("choices_made", [])
        ms.setdefault("ending_scores", {})
        ms.setdefault("rumor_tone", "uncertain")
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

    def _find_choice(self, story: dict[str, Any], choice_id: str) -> dict[str, Any] | None:
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

        self._remove_blocked_choice_events(state, choice)
        self._recalculate_ending_scores(state, story, ms)

        summary = choice.get("summary")
        if summary:
            lines.append(summary)
        return lines

    def _remove_blocked_choice_events(self, state: dict[str, Any], choice: dict[str, Any]) -> None:
        blocked = choice.get("blocks_choices", [])
        if not blocked:
            return
        pending = state.get("flags", {}).get("pending_events", [])
        seed_map = {
            "ally_council_coverup": "story_choice_council",
            "ally_warden_seal": "story_choice_warden",
            "ally_covenant_power": "story_choice_covenant",
            "path_alliance": "story_choice_alliance",
            "path_neutral": "story_choice_neutral",
            "path_betrayal": "story_choice_betrayal",
        }
        for cid in blocked:
            sid = seed_map.get(cid)
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
        amount = story.get("progress_sources", {}).get("flags", {}).get(flag)
        if not amount:
            return []
        return self.add_progress(state, int(amount), reason=flag)

    def on_outcome(self, state: dict[str, Any], outcome: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        choice_id = outcome.get("main_story_choice")
        if choice_id:
            lines.extend(self.apply_choice(state, choice_id))
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
        }
        return True

    def meets_story_requirements(self, state: dict[str, Any], seed: dict[str, Any]) -> bool:
        ms = self.ensure_initialized(state)
        req_phase = seed.get("requires_main_story_phase")
        if req_phase is not None and int(ms.get("phase", 1)) != int(req_phase):
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
