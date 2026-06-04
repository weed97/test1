"""Long-term main story arcs — slow multi-turn world-changing plots."""

from __future__ import annotations

from typing import Any

from utils.io_helpers import load_json
from utils.world_tension import get_tension


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

    def story_def(self, story_id: str) -> dict[str, Any] | None:
        for story in self.load_catalog().get("stories", []):
            if story["id"] == story_id:
                return story
        return None

    def ensure_initialized(self, state: dict[str, Any], *, turn: int = 0) -> dict[str, Any]:
        flags = state.setdefault("flags", {})
        ms = flags.setdefault("main_story", {})
        if not ms.get("id"):
            catalog = self.load_catalog()
            active_quest = flags.get("quests", {}).get("active")
            chosen = catalog.get("default_story", "seal_breaking")
            for story in catalog.get("stories", []):
                if story.get("linked_quest") == active_quest:
                    chosen = story["id"]
                    break
            ms.update(
                {
                    "id": chosen,
                    "stage": 1,
                    "progress": 0,
                    "started_turn": turn,
                    "branch": None,
                }
            )
        ms.setdefault("stage", 1)
        ms.setdefault("progress", 0)
        return ms

    def current(self, state: dict[str, Any]) -> dict[str, Any]:
        return self.ensure_initialized(state)

    def add_progress(self, state: dict[str, Any], amount: int, *, reason: str | None = None) -> list[str]:
        ms = self.ensure_initialized(state)
        story = self.story_def(ms["id"])
        if not story:
            return []
        before = int(ms.get("progress", 0))
        ms["progress"] = min(100, before + int(amount))
        lines: list[str] = []
        if amount and reason:
            lines.append(f"[메인 스토리] {story['title']} +{amount} ({reason})")

        self._maybe_advance_stage(state, story, ms)
        return lines

    def _maybe_advance_stage(self, state: dict[str, Any], story: dict[str, Any], ms: dict[str, Any]) -> None:
        stages = story.get("stages", [])
        stage_idx = int(ms.get("stage", 1)) - 1
        if stage_idx >= len(stages):
            return
        needed = int(stages[stage_idx].get("progress_needed", 100))
        if int(ms.get("progress", 0)) >= needed and stage_idx + 1 < len(stages):
            ms["stage"] = stage_idx + 2
            goal = stages[stage_idx + 1].get("goal", "")
            state.setdefault("flags", {})["main_story_stage_bump"] = goal

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

    def tick(self, state: dict[str, Any], *, turn: int) -> list[str]:
        """Passive progress from tension / faction thresholds."""
        ms = self.ensure_initialized(state, turn=turn)
        story = self.story_def(ms["id"])
        if not story:
            return []
        lines: list[str] = []
        sources = story.get("progress_sources", {})

        tension_min = sources.get("tension_above")
        if tension_min is not None and get_tension(state) >= int(tension_min):
            if turn % 5 == 0:
                lines.extend(self.add_progress(state, 2, reason="세계 긴장"))

        for fid, minimum in (sources.get("faction_min") or {}).items():
            rep = int(state.get("flags", {}).get("faction_reputation", {}).get(fid, 0))
            if rep >= int(minimum) and turn % 7 == 0:
                lines.extend(self.add_progress(state, 1, reason=f"{fid} 영향"))

        bump = state.get("flags", {}).pop("main_story_stage_bump", None)
        if bump:
            lines.append(f"[메인 스토리] {story['title']} — 새 단계: {bump}")

        return lines

    def format_summary(self, state: dict[str, Any]) -> str:
        ms = self.ensure_initialized(state)
        story = self.story_def(ms["id"])
        if not story:
            return "메인 스토리: (미설정)"
        stage = int(ms.get("stage", 1))
        stages = story.get("stages", [])
        goal = stages[stage - 1]["goal"] if stage <= len(stages) else "막바지"
        return (
            f"{story['title']} — {stage}/{len(stages)}단계 | "
            f"진행 {ms.get('progress', 0)}/100 | {goal}"
        )

    def select_story(self, state: dict[str, Any], story_id: str, *, turn: int = 0) -> bool:
        if not self.story_def(story_id):
            return False
        state.setdefault("flags", {})["main_story"] = {
            "id": story_id,
            "stage": 1,
            "progress": 0,
            "started_turn": turn,
            "branch": None,
        }
        return True
