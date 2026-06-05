"""Long-term main story — phases, branching choices, ending tracker."""

from __future__ import annotations

from typing import Any

from utils.io_helpers import load_json
from utils.world_tension import adjust_tension, get_tension


def _current_turn(state: dict[str, Any]) -> int:
    """Turn number for the next player action (1-indexed, matches event_log entries)."""
    log = state.get("event_log", {})
    if isinstance(log, dict):
        entries = log.get("entries", [])
        stored = int(log.get("next_turn", 1))
        if entries:
            last = max(int(e.get("turn", 0)) for e in entries)
            return max(stored, last + 1)
        return max(1, stored)
    return max(1, len(log) + 1)


def _advance_turn_counter(state: dict[str, Any], played_turn: int) -> None:
    log = state.setdefault("event_log", {"next_turn": 1, "entries": []})
    if isinstance(log, dict):
        log["next_turn"] = max(int(log.get("next_turn", 1)), int(played_turn) + 1)


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
                    "mountain_visits": 0,
                    "phase1_subphase": "early",
                    "smoke_seen_turn": None,
                    "phase2_step": 0,
                    "phase2_subphase": "early",
                    "phase3_step": 0,
                    "phase3_subphase": "early",
                }
            )

        ms.setdefault("phase", ms.pop("stage", 1))
        ms.setdefault("progress", 0)
        ms.setdefault("choices_made", [])
        ms.setdefault("ending_scores", {})
        ms.setdefault("rumor_tone", "uncertain")
        ms.setdefault("phase1_step", 0)
        ms.setdefault("factions_contacted", [])
        ms.setdefault("mountain_visits", 0)
        ms.setdefault("phase1_subphase", "early")
        ms.setdefault("smoke_seen_turn", None)
        ms.setdefault("phase2_step", 0)
        ms.setdefault("phase2_subphase", "early")
        ms.setdefault("phase3_step", 0)
        ms.setdefault("phase3_subphase", "early")
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
        lines.extend(self._check_phase2_exit(state, story, ms))
        lines.extend(self._check_phase3_exit(state, story, ms))
        if int(ms.get("progress", 0)) >= 100 and not ms.get("resolved_ending"):
            # Phase 3: ending only after phase3_climax_done (via _complete_phase3 / climax seed).
            if int(ms.get("phase", 1)) >= 3 and not state.get("flags", {}).get("phase3_climax_done"):
                pass
            else:
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
            flags = state.get("flags", {})
            if int(ms.get("phase", 1)) == 1 and not flags.get("phase1_climax_done"):
                return
            if int(ms.get("phase", 1)) == 2 and not flags.get("phase2_climax_done"):
                return
            if int(ms.get("phase", 1)) == 3 and not flags.get("phase3_climax_done"):
                return
            ms["phase"] = phase_idx + 2
            if ms["phase"] == 2:
                self._begin_phase2(state, story, ms)
            elif ms["phase"] == 3:
                self._begin_phase3(state, story, ms)
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
        for pool in ("phase1_choices", "phase2_choices", "phase3_choices"):
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
            ms["phase1_subphase"] = "late"
            amount = story.get("progress_sources", {}).get("flags", {}).get("story_phase1_chosen")
            if amount and "story_phase1_chosen" in (choice.get("flags_set") or {}):
                lines.extend(self.add_progress(state, int(amount), reason="1단계 분기"))
            lines.extend(self._update_climax_readiness(state, story, ms))
            if not state.get("flags", {}).get("phase1_climax_ready"):
                lines.extend(self._check_phase1_exit(state, story, ms))
        elif int(ms.get("phase", 1)) == 2:
            self._advance_phase2_from_flag(state, story, ms, "story_phase2_chosen")
            ms["phase2_subphase"] = "late"
            if choice_id == "path_alliance":
                faction = state.get("flags", {}).get("alliance_faction")
                if faction:
                    ms["alliance_faction"] = faction
                p1 = self._primary_phase1_choice(ms)
                if p1:
                    route = story.get("phase2_alliance_routes", {}).get(p1, {})
                    if route.get("label"):
                        lines.append(f"[동맹] {route['label']} 깃발 아래")
            amount = story.get("progress_sources", {}).get("flags", {}).get("story_phase2_chosen")
            if amount and "story_phase2_chosen" in (choice.get("flags_set") or {}):
                lines.extend(self.add_progress(state, int(amount), reason="2단계 분기"))
            lines.extend(self._update_phase2_climax_readiness(state, story, ms))
            if not state.get("flags", {}).get("phase2_climax_ready"):
                lines.extend(self._check_phase2_exit(state, story, ms))
        elif int(ms.get("phase", 1)) == 3:
            self._advance_phase3_from_flag(state, story, ms, "story_phase3_chosen")
            ms["phase3_subphase"] = "late"
            amount = story.get("progress_sources", {}).get("flags", {}).get("story_phase3_chosen")
            if amount and "story_phase3_chosen" in (choice.get("flags_set") or {}):
                lines.extend(self.add_progress(state, int(amount), reason="3단계 최후 선택"))
            lines.extend(self._update_phase3_climax_readiness(state, story, ms))
            if not state.get("flags", {}).get("phase3_climax_ready"):
                lines.extend(self._check_phase3_exit(state, story, ms))

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
            "path_neutral": "story_choice_neutral",
            "path_betrayal": "story_choice_betrayal",
            "final_reinforce": "story_choice_final_reinforce",
            "final_break": "story_choice_final_break",
            "final_chaos": "story_choice_final_chaos",
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
            if cid == "path_alliance":
                for sid in self._alliance_branch_seed_ids(story):
                    while sid in pending:
                        pending.remove(sid)
                continue
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
        *,
        turn: int | None = None,
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 1:
            return []
        flow = self._phase1_flow(story)
        flags_to_step = flow.get("flags_to_step", {})
        step = flags_to_step.get(flag)
        if step is None and flag not in ("black_smoke_seen",):
            return []
        lines: list[str] = []
        current = int(ms.get("phase1_step", 0))

        if flag == "black_smoke_seen":
            ms["phase1_subphase"] = "early"
            if ms.get("smoke_seen_turn") is None:
                ms["smoke_seen_turn"] = turn if turn is not None else _current_turn(state)
            if current < 1:
                ms["phase1_step"] = 1
                lines.extend(self._queue_phase1_step_events(state, story, ms, 1))

        if step is not None and int(step) > current:
            ms["phase1_step"] = int(step)
            lines.extend(self._queue_phase1_step_events(state, story, ms, int(step)))

        if flag == "phase1_rumors_spread":
            state.setdefault("flags", {})["phase1_factions_active"] = True
            ms["phase1_subphase"] = "mid"
            if int(ms.get("phase1_step", 0)) < 3:
                ms["phase1_step"] = 3
                lines.extend(self._queue_phase1_step_events(state, story, ms, 3))
            lines.extend(self._queue_phase1_step_events(state, story, ms, 2))

        if flag == "phase1_climax_done":
            ms["phase1_subphase"] = "climax"

        return lines

    def record_mountain_visit(self, state: dict[str, Any], *, found: bool = False) -> list[str]:
        ms = self.ensure_initialized(state)
        story = self.story_def(ms["id"])
        if not story or int(ms.get("phase", 1)) != 1:
            return []
        ms["mountain_visits"] = int(ms.get("mountain_visits", 0)) + 1
        flags = state.setdefault("flags", {})
        flags["phase1_mountain_visited"] = True
        if found:
            flags["phase1_mountain_found"] = True
        lines = [f"[1단계] 북쪽 산 방문 ({ms['mountain_visits']}회)"]
        if flags.get("phase1_elder_request") and not flags.get("phase1_elder_responded"):
            pending = int(ms.get("elder_pending_mountain_visits", 0)) + 1
            ms["elder_pending_mountain_visits"] = pending
            if pending == 1:
                lines.append(
                    "[1단계] 장로의 부탁을 아직 받지 않은 채 산길에 섰다. "
                    "마을에서 눈치 보는 시선이 느껴진다."
                )
            elif pending >= 2:
                flags["phase1_elder_declined"] = True
                flags["phase1_elder_responded"] = True
                from utils.faction_engine import FactionEngine

                lines.extend(
                    FactionEngine(self.base_dir).apply_reputation_outcome(
                        state, {"faction_reputation": {"ashpoint_council": -6}}
                    )
                )
                lines.append(
                    "[1단계] 장로의 부탁을 거두치 않고 산으로 향했다. "
                    "자치회는 당신을 '독단적인 이방인'으로 기록하기 시작한다."
                )
        if story:
            lines.extend(self._update_climax_readiness(state, story, ms))
        return lines

    def _climax_conditions_met(self, state: dict[str, Any], story: dict[str, Any], ms: dict[str, Any]) -> tuple[int, list[str]]:
        return self._climax_gate_conditions_met(state, ms, story.get("phase1_climax_gate", {}))

    def _update_climax_readiness(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 1:
            return []
        if not state.get("flags", {}).get("story_phase1_chosen"):
            return []
        if state.get("flags", {}).get("phase1_climax_done"):
            return []
        gate = story.get("phase1_climax_gate", {})
        required = int(gate.get("required_count", 2))
        count, met_ids = self._climax_conditions_met(state, story, ms)
        ms["climax_conditions_met"] = met_ids
        if count < required:
            return []
        flags = state.setdefault("flags", {})
        if flags.get("phase1_climax_ready"):
            return []
        flags["phase1_climax_ready"] = True
        ms["phase1_subphase"] = "climax"
        pending = flags.setdefault("pending_events", [])
        for seed_id in self._phase1_flow(story).get("climax_seeds", []):
            if seed_id not in pending:
                pending.append(seed_id)
        return [f"[1단계 클라이맥스] 조건 {count}/{len(gate.get('conditions', []))} 충족 — 봉인의 첫 균열 임박"]

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
        lines.extend(self._update_climax_readiness(state, story, ms))
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
            req_flag = rule.get("requires_flag")
            if req_flag and not flags.get(req_flag):
                continue
            if rule.get("flag") and flags.get(rule["flag"]):
                return self._complete_phase1(state, story, ms, rule["flag"])
            if rule.get("faction_rep_min") is not None:
                threshold = int(rule["faction_rep_min"])
                if any(int(v) >= threshold for v in faction_rep.values()):
                    return self._complete_phase1(state, story, ms, "faction_alliance")
            if rule.get("tension_min") is not None and get_tension(state) >= int(rule["tension_min"]):
                return self._complete_phase1(state, story, ms, "tension")
            if rule.get("factions_contacted_min") is not None:
                minimum = int(rule["factions_contacted_min"])
                if len(ms.get("factions_contacted", [])) >= minimum:
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
            self._begin_phase2(state, story, ms)
        self._maybe_queue_phase_events(state, story, ms, phase1_needed - 1)
        return [f"[1단계 완료] 균열의 전조 — {reason}"]

    def _primary_phase1_choice(self, ms: dict[str, Any]) -> str | None:
        for cid in (
            "ally_village",
            "seek_truth",
            "pursue_power",
            "exploit_chaos",
            "stay_neutral",
        ):
            if cid in ms.get("choices_made", []):
                return cid
        return None

    def _alliance_route_spec(self, story: dict[str, Any], ms: dict[str, Any]) -> dict[str, Any]:
        p1 = self._primary_phase1_choice(ms)
        if not p1:
            return {}
        return story.get("phase2_alliance_routes", {}).get(p1, {})

    def _phase3_alliance_route_spec(self, story: dict[str, Any], ms: dict[str, Any]) -> dict[str, Any]:
        p1 = self._primary_phase1_choice(ms)
        if not p1:
            return {}
        return story.get("phase3_alliance_routes", {}).get(p1, {})

    def _alliance_branch_seed_ids(self, story: dict[str, Any]) -> list[str]:
        routes = story.get("phase2_alliance_routes", {})
        return [spec["choice_seed"] for spec in routes.values() if spec.get("choice_seed")]

    def _primary_phase2_choice(self, ms: dict[str, Any]) -> str | None:
        for cid in ("path_alliance", "path_neutral", "path_betrayal"):
            if cid in ms.get("choices_made", []):
                return cid
        return None

    def _climax_gate_conditions_met(
        self, state: dict[str, Any], ms: dict[str, Any], gate: dict[str, Any]
    ) -> tuple[int, list[str]]:
        conditions = gate.get("conditions", [])
        flags = state.get("flags", {})
        faction_rep = flags.get("faction_reputation", {})
        met: list[str] = []
        for cond in conditions:
            cid = cond.get("id", "")
            if cond.get("tension_min") is not None and get_tension(state) >= int(cond["tension_min"]):
                met.append(cid)
            elif cond.get("faction_rep_min") is not None:
                if any(int(v) >= int(cond["faction_rep_min"]) for v in faction_rep.values()):
                    met.append(cid)
            elif cond.get("flag") and flags.get(cond["flag"]):
                met.append(cid)
            elif cond.get("mountain_visits_min") is not None:
                if int(ms.get("mountain_visits", 0)) >= int(cond["mountain_visits_min"]):
                    met.append(cid)
            elif cond.get("factions_contacted_min") is not None:
                if len(ms.get("factions_contacted", [])) >= int(cond["factions_contacted_min"]):
                    met.append(cid)
        return len(met), met

    def _applicable_climax_seeds(self, story: dict[str, Any], ms: dict[str, Any], *, phase: int) -> list[str]:
        flow = story.get(f"phase{phase}_flow", {})
        all_ids = list(flow.get("climax_seeds", []))
        p1 = self._primary_phase1_choice(ms)
        p2 = self._primary_phase2_choice(ms)
        if phase == 2:
            if p2 == "path_alliance" and p1:
                spec = story.get("phase2_alliance_routes", {}).get(p1, {})
                sid = spec.get("climax_seed")
                return [sid] if sid else []
            if p2 == "path_neutral":
                return ["phase2_climax_neutral"]
            if p2 == "path_betrayal":
                return ["phase2_climax_betrayal"]
        if phase == 3:
            if p2 == "path_alliance" and p1:
                spec = story.get("phase3_alliance_routes", {}).get(p1, {})
                sid = spec.get("climax_seed")
                return [sid] if sid else []
            if p2 == "path_neutral":
                return ["phase3_climax_neutral"]
            if p2 == "path_betrayal":
                return ["phase3_climax_betrayal"]
        return all_ids

    def _phase2_flow(self, story: dict[str, Any]) -> dict[str, Any]:
        return story.get("phase2_flow", {})

    def _begin_phase2(self, state: dict[str, Any], story: dict[str, Any], ms: dict[str, Any]) -> list[str]:
        if int(ms.get("phase", 1)) != 2 or ms.get("phase2_begun"):
            return []
        ms["phase2_begun"] = True
        ms["phase2_subphase"] = "early"
        if int(ms.get("phase2_step", 0)) < 1:
            ms["phase2_step"] = 1
        return self._queue_phase2_step_events(state, story, ms, 1)

    def _advance_phase2_from_flag(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
        flag: str,
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 2:
            return []
        flow = self._phase2_flow(story)
        flags_to_step = flow.get("flags_to_step", {})
        step = flags_to_step.get(flag)
        lines: list[str] = []
        current = int(ms.get("phase2_step", 0))

        if flag == "story_faction_clash_seen" and not state.get("flags", {}).get("phase2_escalation_done"):
            if state.get("flags", {}).get("phase2_opening_done"):
                state.setdefault("flags", {})["phase2_escalation_done"] = True
                flag = "phase2_escalation_done"
            else:
                return lines

        if step is not None and int(step) > current:
            ms["phase2_step"] = int(step)
            lines.extend(self._queue_phase2_step_events(state, story, ms, int(step)))

        if flag == "phase2_opening_done":
            ms["phase2_subphase"] = "early"
            if int(ms.get("phase2_step", 0)) < 2:
                ms["phase2_step"] = max(int(ms.get("phase2_step", 0)), 1)
                lines.extend(self._queue_phase2_step_events(state, story, ms, 2))

        if flag == "phase2_escalation_done":
            ms["phase2_subphase"] = "mid"
            if int(ms.get("phase2_step", 0)) < 3:
                ms["phase2_step"] = 3
                lines.extend(self._queue_phase2_step_events(state, story, ms, 3))

        if flag == "story_phase2_chosen":
            ms["phase2_subphase"] = "late"

        if flag == "phase2_climax_done":
            ms["phase2_subphase"] = "climax"

        return lines

    def _phase2_escalation_count(self, state: dict[str, Any]) -> int:
        flags = state.get("flags", {})
        count = 0
        for key in (
            "phase2_faction_raid",
            "phase2_merchant_blockade",
            "phase2_warden_line",
            "story_faction_clash_seen",
            "story_trade_opportunist",
            "story_blackfang_chaos",
        ):
            if flags.get(key):
                count += 1
        return count

    def _queue_phase2_step_events(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
        step: int,
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 2:
            return []
        flow = self._phase2_flow(story)
        step_queue = flow.get("step_queue", {})
        events = step_queue.get(str(step), [])
        if step == 3:
            min_esc = int(flow.get("branch_queue_min_escalation", 1))
            if self._phase2_escalation_count(state) < min_esc:
                return []
            if state.get("flags", {}).get("story_phase2_chosen"):
                return []
        pending = state.setdefault("flags", {}).setdefault("pending_events", [])
        added: list[str] = []
        for event_id in events:
            if event_id not in pending:
                pending.append(event_id)
                added.append(event_id)
        if added and step == 3:
            return ["[2단계] 세력 견제 후 2단계 분기점이 열렸다."]
        return []

    def _phase2_climax_conditions_met(
        self, state: dict[str, Any], story: dict[str, Any], ms: dict[str, Any]
    ) -> tuple[int, list[str]]:
        return self._climax_gate_conditions_met(state, ms, story.get("phase2_climax_gate", {}))

    def _update_phase2_climax_readiness(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 2:
            return []
        if not state.get("flags", {}).get("story_phase2_chosen"):
            return []
        if state.get("flags", {}).get("phase2_climax_done"):
            return []
        gate = story.get("phase2_climax_gate", {})
        required = int(gate.get("required_count", 2))
        count, met_ids = self._phase2_climax_conditions_met(state, story, ms)
        ms["phase2_climax_conditions_met"] = met_ids
        if count < required:
            return []
        flags = state.setdefault("flags", {})
        if flags.get("phase2_climax_ready"):
            return []
        flags["phase2_climax_ready"] = True
        ms["phase2_subphase"] = "climax"
        pending = flags.setdefault("pending_events", [])
        for seed_id in self._applicable_climax_seeds(story, ms, phase=2):
            if seed_id not in pending:
                pending.append(seed_id)
        return [f"[2단계 클라이맥스] 조건 {count}/{len(gate.get('conditions', []))} 충족 — 판의 균열 임박"]

    def _check_phase2_exit(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 2 or ms.get("phase2_complete"):
            return []
        exit_cfg = story.get("phase2_exit")
        if not exit_cfg:
            return []
        if int(ms.get("progress", 0)) < int(exit_cfg.get("min_progress", 0)):
            return []
        flags = state.get("flags", {})
        for rule in exit_cfg.get("any_of", []):
            if rule.get("flag") and flags.get(rule["flag"]):
                return self._complete_phase2(state, story, ms, rule["flag"])
        return []

    def _complete_phase2(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
        reason: str,
    ) -> list[str]:
        ms["phase2_complete"] = True
        phases = story.get("phases", [])
        phase2_needed = int(phases[1].get("progress_needed", 65)) if len(phases) > 1 else 65
        if int(ms.get("progress", 0)) < phase2_needed:
            ms["progress"] = phase2_needed
        if int(ms.get("phase", 1)) == 2:
            ms["phase"] = 3
            next_name = phases[2]["name"] if len(phases) > 2 else "3단계"
            state.setdefault("flags", {})["main_story_phase_bump"] = next_name
            self._begin_phase3(state, story, ms)
        self._maybe_queue_phase_events(state, story, ms, phase2_needed - 1)
        return [f"[2단계 완료] 세력의 대립 — {reason}"]

    def _phase3_flow(self, story: dict[str, Any]) -> dict[str, Any]:
        return story.get("phase3_flow", {})

    def _begin_phase3(self, state: dict[str, Any], story: dict[str, Any], ms: dict[str, Any]) -> list[str]:
        if int(ms.get("phase", 1)) != 3 or ms.get("phase3_begun"):
            return []
        ms["phase3_begun"] = True
        ms["phase3_subphase"] = "early"
        if int(ms.get("phase3_step", 0)) < 1:
            ms["phase3_step"] = 1
        return self._queue_phase3_step_events(state, story, ms, 1)

    def _advance_phase3_from_flag(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
        flag: str,
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 3:
            return []
        flow = self._phase3_flow(story)
        flags_to_step = flow.get("flags_to_step", {})
        step = flags_to_step.get(flag)
        lines: list[str] = []
        current = int(ms.get("phase3_step", 0))

        if flag == "story_seal_near_break" and not state.get("flags", {}).get("phase3_crisis_done"):
            state.setdefault("flags", {})["phase3_crisis_done"] = True
            flag = "phase3_crisis_done"

        if step is not None and int(step) > current:
            ms["phase3_step"] = int(step)
            lines.extend(self._queue_phase3_step_events(state, story, ms, int(step)))

        if flag == "phase3_opening_done":
            ms["phase3_subphase"] = "early"
            if int(ms.get("phase3_step", 0)) < 2:
                ms["phase3_step"] = max(int(ms.get("phase3_step", 0)), 1)
                lines.extend(self._queue_phase3_step_events(state, story, ms, 2))

        if flag == "phase3_crisis_done":
            ms["phase3_subphase"] = "mid"
            if int(ms.get("phase3_step", 0)) < 3:
                ms["phase3_step"] = 3
                lines.extend(self._queue_phase3_step_events(state, story, ms, 3))

        if flag == "story_phase3_chosen":
            ms["phase3_subphase"] = "late"

        if flag == "phase3_climax_done":
            ms["phase3_subphase"] = "climax"

        return lines

    def _phase3_crisis_count(self, state: dict[str, Any]) -> int:
        flags = state.get("flags", {})
        count = 0
        for key in (
            "story_seal_near_break",
            "phase3_faction_ultimatum",
            "phase3_covenant_final_offer",
        ):
            if flags.get(key):
                count += 1
        return count

    def _queue_phase3_step_events(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
        step: int,
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 3:
            return []
        flow = self._phase3_flow(story)
        step_queue = flow.get("step_queue", {})
        events = step_queue.get(str(step), [])
        if step == 3:
            min_crisis = int(flow.get("branch_queue_min_crisis", 1))
            if self._phase3_crisis_count(state) < min_crisis:
                return []
            if state.get("flags", {}).get("story_phase3_chosen"):
                return []
        pending = state.setdefault("flags", {}).setdefault("pending_events", [])
        added: list[str] = []
        for event_id in events:
            if event_id not in pending:
                pending.append(event_id)
                added.append(event_id)
        if added and step == 3:
            return ["[3단계] 봉인 직전 — 최후의 선택지가 열렸다."]
        return []

    def _phase3_climax_conditions_met(
        self, state: dict[str, Any], story: dict[str, Any], ms: dict[str, Any]
    ) -> tuple[int, list[str]]:
        return self._climax_gate_conditions_met(state, ms, story.get("phase3_climax_gate", {}))

    def _update_phase3_climax_readiness(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 3:
            return []
        if not state.get("flags", {}).get("story_phase3_chosen"):
            return []
        if state.get("flags", {}).get("phase3_climax_done"):
            return []
        gate = story.get("phase3_climax_gate", {})
        required = int(gate.get("required_count", 2))
        count, met_ids = self._phase3_climax_conditions_met(state, story, ms)
        ms["phase3_climax_conditions_met"] = met_ids
        if count < required:
            return []
        flags = state.setdefault("flags", {})
        if flags.get("phase3_climax_ready"):
            return []
        flags["phase3_climax_ready"] = True
        ms["phase3_subphase"] = "climax"
        pending = flags.setdefault("pending_events", [])
        for seed_id in self._applicable_climax_seeds(story, ms, phase=3):
            if seed_id not in pending:
                pending.append(seed_id)
        return [f"[3단계 클라이맥스] 조건 {count}/{len(gate.get('conditions', []))} 충족 — 결말의 문 임박"]

    def _check_phase3_exit(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
    ) -> list[str]:
        if int(ms.get("phase", 1)) != 3 or ms.get("phase3_complete"):
            return []
        exit_cfg = story.get("phase3_exit")
        if not exit_cfg:
            return []
        if int(ms.get("progress", 0)) < int(exit_cfg.get("min_progress", 0)):
            return []
        flags = state.get("flags", {})
        for rule in exit_cfg.get("any_of", []):
            if rule.get("flag") and flags.get(rule["flag"]):
                return self._complete_phase3(state, story, ms, rule["flag"])
        return []

    def _complete_phase3(
        self,
        state: dict[str, Any],
        story: dict[str, Any],
        ms: dict[str, Any],
        reason: str,
    ) -> list[str]:
        ms["phase3_complete"] = True
        phases = story.get("phases", [])
        phase3_needed = int(phases[2].get("progress_needed", 100)) if len(phases) > 2 else 100
        if int(ms.get("progress", 0)) < phase3_needed:
            ms["progress"] = phase3_needed
        lines = [f"[3단계 완료] 최후의 선택 — {reason}"]
        if not ms.get("resolved_ending"):
            lines.extend(self._try_resolve_ending(state, story, ms))
        return lines

    def _phase3_step_label(self, story: dict[str, Any], step: int) -> str:
        labels = {
            0: "대기",
            1: "봉인 직전",
            2: "최후의 압박",
            3: "최후의 선택",
            4: "결말의 문",
        }
        return labels.get(step, f"단계 {step}")

    def _phase3_next_hint(self, state: dict[str, Any], ms: dict[str, Any], story: dict[str, Any]) -> str | None:
        flags = state.get("flags", {})
        if int(ms.get("phase", 1)) != 3 or flags.get("phase3_climax_done") or ms.get("resolved_ending"):
            return None
        if flags.get("phase3_climax_ready"):
            path2 = next((c for c in reversed(ms.get("choices_made", [])) if c.startswith("path_")), None)
            return {
                "path_alliance": "관측탑·숲 — 동맹과 함께 결말의 문을 열어라",
                "path_neutral": "탑·숲 — 홀로 결말의 문 앞에 서라",
                "path_betrayal": "탑·숲 — 배신의 각인을 새겨라",
            }.get(path2 or "", "관측탑·숲 — 결말의 문을 완료하라")
        if flags.get("story_phase3_chosen"):
            gate = story.get("phase3_climax_gate", {})
            required = int(gate.get("required_count", 2))
            _, met = self._phase3_climax_conditions_met(state, story, ms)
            missing: list[str] = []
            for cond in gate.get("conditions", []):
                cid = cond.get("id", "")
                if cid in met:
                    continue
                if cond.get("tension_min") is not None:
                    missing.append(f"긴장 {cond['tension_min']}+")
                elif cond.get("faction_rep_min") is not None:
                    missing.append(f"세력 평판 {cond['faction_rep_min']}+")
                elif cond.get("flag"):
                    missing.append(cond["flag"])
            if missing:
                return f"결말 준비 ({len(met)}/{required}) — {', '.join(missing[:2])}"
            return "결말 준비 완료 — 관측탑으로 향하라"
        crisis = self._phase3_crisis_count(state)
        min_crisis = int(self._phase3_flow(story).get("branch_queue_min_crisis", 1))
        if crisis >= min_crisis and not flags.get("story_phase3_chosen"):
            return "탑·숲·마을 — 봉인 강화·해제·혼돈 중 하나를 선택하라"
        if flags.get("phase3_opening_done"):
            return "탑·숲 탐색 — 봉인 직전의 압박을 견뎌라"
        return "관측탑·숲 — 봉인 경보를 확인하라"

    def _phase2_step_label(self, story: dict[str, Any], step: int) -> str:
        labels = {
            0: "대기",
            1: "세력 동원",
            2: "견제와 협상",
            3: "2단계 분기",
            4: "판의 균열",
        }
        return labels.get(step, f"단계 {step}")

    def _phase2_next_hint(self, state: dict[str, Any], ms: dict[str, Any], story: dict[str, Any]) -> str | None:
        flags = state.get("flags", {})
        if int(ms.get("phase", 1)) != 2 or flags.get("phase2_climax_done"):
            return None
        if flags.get("phase2_climax_ready"):
            choice = next((c for c in reversed(ms.get("choices_made", [])) if c.startswith("path_")), None)
            if choice == "path_alliance":
                label = self._alliance_route_spec(story, ms).get("label", "동맹")
                return f"숲·탑 — {label} 깃발 아래 균열을 막아라"
            route = {
                "path_neutral": "마을·숲 — 어느 편도 아닌 채 판을 견제하라",
                "path_betrayal": "숲·탑 — 약속을 깨고 판을 뒤집어라",
            }.get(choice or "", "숲·탑 — 2단계 클라이맥스를 완료하라")
            return route
        if flags.get("story_phase2_chosen"):
            gate = story.get("phase2_climax_gate", {})
            required = int(gate.get("required_count", 2))
            _, met = self._phase2_climax_conditions_met(state, story, ms)
            missing: list[str] = []
            for cond in gate.get("conditions", []):
                cid = cond.get("id", "")
                if cid in met:
                    continue
                if cond.get("tension_min") is not None:
                    missing.append(f"긴장 {cond['tension_min']}+")
                elif cond.get("faction_rep_min") is not None:
                    missing.append(f"세력 평판 {cond['faction_rep_min']}+")
                elif cond.get("flag"):
                    missing.append(cond["flag"])
            if missing:
                return f"클라이맥스 준비 ({len(met)}/{required}) — {', '.join(missing[:2])}"
            return "클라이맥스 조건 충족 — 숲·탑으로 향하라"
        esc = self._phase2_escalation_count(state)
        min_esc = int(self._phase2_flow(story).get("branch_queue_min_escalation", 1))
        if esc >= min_esc and not flags.get("story_phase2_chosen"):
            return "마을·숲 대화·탐색 — 동맹·중립·배신 중 하나를 선택하라"
        if flags.get("phase2_opening_done"):
            return "마을·숲 탐색 — 세력 견제와 봉인 진동을 살펴라"
        return "마을 대화 — 자치회 긴급 소집에 응하라"

    def _phase1_step_label(self, story: dict[str, Any], step: int) -> str:
        sub = {
            "early": "【초반】검은 연기의 시작",
            "mid": "【중반】세력들의 움직임",
            "late": "【후반】첫 번째 분기",
            "climax": "【클라이맥스】봉인의 첫 균열",
        }
        sections = self._phase1_flow(story).get("sections", {})
        labels = {
            0: "대기",
            1: "검은 연기 목격",
            2: "소문 확산",
            3: "세력 움직임",
            4: "첫 분기",
            5: "봉인 첫 균열",
        }
        return labels.get(step, f"단계 {step}")

    def _phase1_next_hint(self, state: dict[str, Any], ms: dict[str, Any], story: dict[str, Any]) -> str | None:
        flags = state.get("flags", {})
        if int(ms.get("phase", 1)) != 1 or flags.get("phase1_climax_done"):
            return None
        if flags.get("phase1_climax_ready"):
            choice = next((c for c in ms.get("choices_made", []) if c), None)
            route = {
                "ally_village": "마을·숲 — 민병대와 함께 균열을 막아라",
                "pursue_power": "탑·숲 — 봉인에서 새어 나오는 힘을 목격하라",
                "seek_truth": "탑·숲 — 감시자와 함께 봉인 기록을 확인하라",
                "exploit_chaos": "마을·숲 — 혼란 속에서 내려오는 괴물을 목격하라",
                "stay_neutral": "탑·숲 — 어느 편도 아닌 채 균열을 바라보라",
            }.get(choice or "", "숲·탑 탐색 — 봉인의 첫 균열을 목격하라")
            return route
        if flags.get("story_phase1_chosen"):
            gate = story.get("phase1_climax_gate", {})
            required = int(gate.get("required_count", 2))
            _, met = self._climax_conditions_met(state, story, ms)
            missing: list[str] = []
            for cond in gate.get("conditions", []):
                cid = cond.get("id", "")
                if cid in met:
                    continue
                if cond.get("tension_min") is not None:
                    missing.append(f"긴장 {cond['tension_min']}+")
                elif cond.get("faction_rep_min") is not None:
                    missing.append(f"세력 평판 {cond['faction_rep_min']}+")
                elif cond.get("mountain_visits_min") is not None:
                    missing.append(f"산 방문 {cond['mountain_visits_min']}회")
                elif cond.get("factions_contacted_min") is not None:
                    missing.append(f"세력 접촉 {cond['factions_contacted_min']}곳")
            if missing:
                return f"클라이맥스 준비 ({len(met)}/{required}) — {', '.join(missing[:2])}"
            return "클라이맥스 조건 충족 — 숲·탑으로 향하라"
        contacts = len(ms.get("factions_contacted", []))
        if int(ms.get("phase1_step", 0)) >= 3 and contacts >= 1 and not flags.get("story_phase1_chosen"):
            return "마을·숲 대화·탐색 — A~E 첫 분기 선택지를 찾아라"
        if flags.get("phase1_elder_request") and not flags.get("phase1_elder_responded"):
            return "장로 마렌과 대화(수락) 또는 산 탐색(거절) — 부탁에 답하라"
        if flags.get("phase1_rumors_spread"):
            return "마을 대화·탐색 — 장로 부탁과 세력들의 움직임을 살펴라"
        if flags.get("black_smoke_seen"):
            return "마을 대화·휴식 — 소문이 퍼질 때까지 2턴 정도 기다려라"
        return "마을 탐색 — 북쪽 산의 검은 연기를 목격하라"

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

    def on_flag_set(self, state: dict[str, Any], flag: str, *, turn: int | None = None) -> list[str]:
        ms = self.ensure_initialized(state)
        story = self.story_def(ms["id"])
        if not story:
            return []
        lines: list[str] = []
        if flag == "black_smoke_seen" and ms.get("smoke_seen_turn") is None:
            ms["smoke_seen_turn"] = turn if turn is not None else _current_turn(state)
        lines.extend(self._advance_phase1_from_flag(state, story, ms, flag, turn=turn))
        if int(ms.get("phase", 1)) == 2:
            lines.extend(self._advance_phase2_from_flag(state, story, ms, flag))
        if int(ms.get("phase", 1)) == 3:
            lines.extend(self._advance_phase3_from_flag(state, story, ms, flag))
        amount = story.get("progress_sources", {}).get("flags", {}).get(flag)
        if amount:
            lines.extend(self.add_progress(state, int(amount), reason=flag))
        else:
            phase = int(ms.get("phase", 1))
            if phase == 3:
                lines.extend(self._update_phase3_climax_readiness(state, story, ms))
                lines.extend(self._check_phase3_exit(state, story, ms))
            elif phase == 2:
                lines.extend(self._update_phase2_climax_readiness(state, story, ms))
                lines.extend(self._check_phase2_exit(state, story, ms))
            else:
                lines.extend(self._update_climax_readiness(state, story, ms))
                lines.extend(self._check_phase1_exit(state, story, ms))
        return lines

    def on_outcome(self, state: dict[str, Any], outcome: dict[str, Any], *, turn: int | None = None) -> list[str]:
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
                lines.extend(self._advance_phase1_from_flag(state, story, ms, p1_flag, turn=turn))
        p2_flag = outcome.get("main_story_phase2_flag")
        if p2_flag:
            ms = self.ensure_initialized(state)
            story = self.story_def(ms["id"])
            if story:
                lines.extend(self._advance_phase2_from_flag(state, story, ms, p2_flag))
        p3_flag = outcome.get("main_story_phase3_flag")
        if p3_flag:
            ms = self.ensure_initialized(state)
            story = self.story_def(ms["id"])
            if story:
                lines.extend(self._advance_phase3_from_flag(state, story, ms, p3_flag))
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
        lines.extend(self._update_climax_readiness(state, story, ms))
        lines.extend(self._check_phase1_exit(state, story, ms))
        if int(ms.get("phase", 1)) == 2:
            self._begin_phase2(state, story, ms)
        lines.extend(self._update_phase2_climax_readiness(state, story, ms))
        lines.extend(self._check_phase2_exit(state, story, ms))
        if int(ms.get("phase", 1)) == 3:
            self._begin_phase3(state, story, ms)
        lines.extend(self._update_phase3_climax_readiness(state, story, ms))
        lines.extend(self._check_phase3_exit(state, story, ms))
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
            visits = int(ms.get("mountain_visits", 0))
            sub = ms.get("phase1_subphase", "early")
            sections = self._phase1_flow(story).get("sections", {})
            section_name = sections.get(sub, {}).get("name", sub)
            parts.append(
                f"1단계 [{section_name}] {self._phase1_step_label(story, step)} | "
                f"세력 {contacts} · 산 {visits}회"
            )
            met = ms.get("climax_conditions_met", [])
            if met and not state.get("flags", {}).get("phase1_climax_done"):
                parts.append(f"클라이맥스 조건: {len(met)}/4 ({', '.join(met)})")
            hint = self._phase1_next_hint(state, ms, story)
            if hint:
                parts.append(f"다음: {hint}")
        elif phase == 2:
            step = int(ms.get("phase2_step", 0))
            sub = ms.get("phase2_subphase", "early")
            sections = self._phase2_flow(story).get("sections", {})
            section_name = sections.get(sub, {}).get("name", sub)
            esc = self._phase2_escalation_count(state)
            alliance = self._alliance_route_spec(story, ms).get("label")
            alliance_bit = f" · 동맹 {alliance}" if alliance and "path_alliance" in ms.get("choices_made", []) else ""
            parts.append(
                f"2단계 [{section_name}] {self._phase2_step_label(story, step)} | "
                f"견제 이벤트 {esc}{alliance_bit}"
            )
            met = ms.get("phase2_climax_conditions_met", [])
            if met and not state.get("flags", {}).get("phase2_climax_done"):
                parts.append(f"클라이맥스 조건: {len(met)}/4 ({', '.join(met)})")
            hint = self._phase2_next_hint(state, ms, story)
            if hint:
                parts.append(f"다음: {hint}")
        elif phase == 3 and not ms.get("resolved_ending"):
            step = int(ms.get("phase3_step", 0))
            sub = ms.get("phase3_subphase", "early")
            sections = self._phase3_flow(story).get("sections", {})
            section_name = sections.get(sub, {}).get("name", sub)
            crisis = self._phase3_crisis_count(state)
            parts.append(
                f"3단계 [{section_name}] {self._phase3_step_label(story, step)} | "
                f"위기 이벤트 {crisis}"
            )
            met = ms.get("phase3_climax_conditions_met", [])
            if met and not state.get("flags", {}).get("phase3_climax_done"):
                parts.append(f"결말 조건: {len(met)}/4 ({', '.join(met)})")
            hint = self._phase3_next_hint(state, ms, story)
            if hint:
                parts.append(f"다음: {hint}")
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
            "phase2_step": 0,
            "phase2_subphase": "early",
            "phase3_step": 0,
            "phase3_subphase": "early",
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
        req_choices = seed.get("requires_main_story_choices")
        if req_choices:
            made = set(ms.get("choices_made", []))
            if not all(c in made for c in req_choices):
                return False
        not_choice = seed.get("requires_not_main_story_choice")
        if not_choice and not_choice in ms.get("choices_made", []):
            return False
        turns_since = seed.get("requires_main_story_turns_since_smoke_min")
        if turns_since is not None:
            smoke_turn = ms.get("smoke_seen_turn")
            if smoke_turn is None:
                return False
            if _current_turn(state) - int(smoke_turn) < int(turns_since):
                return False
        mv_min = seed.get("requires_main_story_mountain_visits_min")
        if mv_min is not None and int(ms.get("mountain_visits", 0)) < int(mv_min):
            return False
        return True
