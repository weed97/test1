"""On-demand lore and event seed loading for LLM context (not stored in world_state)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from utils.io_helpers import load_json, load_text


def _slugify(text: str) -> str:
    return re.sub(r"[^\w가-힣]+", "-", text.strip().lower()).strip("-")


class ContentLoader:
    """Load rich narrative content only when needed for LLM prompts."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir)
        self.lore_dir = self.base_dir / "lore"
        self.events_dir = self.base_dir / "events"
        self._seeds_cache: dict[str, Any] | None = None
        self._quests_cache: dict[str, Any] | None = None
        self._dialogues_cache: dict[str, list[str]] | None = None

    def load_quests(self) -> dict[str, dict[str, Any]]:
        path = self.events_dir / "quests.json"
        if not path.exists():
            return {}
        if self._quests_cache is None:
            data = load_json(path)
            self._quests_cache = {q["id"]: q for q in data.get("quests", [])}
        return self._quests_cache

    def load_npc_dialogues(self, npc_id: str, state: dict[str, Any] | None = None) -> list[str]:
        path = self.events_dir / "dialogues.json"
        if not path.exists():
            return []
        if self._dialogues_cache is None:
            self._dialogues_cache = load_json(path)
        entry = self._dialogues_cache.get(npc_id, [])
        if isinstance(entry, list):
            return entry
        if not isinstance(entry, dict):
            return []

        flags = state.get("flags", {}) if state else {}
        quests = flags.get("quests", {})
        active = quests.get("active")
        stage = int(quests.get("stage", 1))
        pools: list[str] = []

        for flag, lines in entry.get("by_flag", {}).items():
            if flags.get(flag):
                pools.extend(lines)

        ms = flags.get("main_story", {})
        if int(ms.get("phase", 0)) == 1:
            sub = ms.get("phase1_subphase")
            if sub:
                pools.extend(entry.get("by_main_story_phase", {}).get(sub, []))

        stage_key = f"{active}:{stage}" if active else ""
        stage_lines = entry.get("by_quest_stage", {}).get(stage_key, [])
        if stage_lines:
            pools.extend(stage_lines)

        if pools:
            return pools
        return entry.get("default", [])

    def get_active_quest(self, state: dict[str, Any]) -> dict[str, Any] | None:
        qid = state.get("flags", {}).get("quests", {}).get("active")
        if not qid:
            return None
        return self.load_quests().get(qid)

    def load_event_seeds(self) -> dict[str, dict[str, Any]]:
        if self._seeds_cache is not None:
            return self._seeds_cache

        merged: dict[str, dict[str, Any]] = {}
        manifest = self.events_dir / "seeds.json"
        if manifest.exists():
            data = load_json(manifest)
            for seed in data.get("seeds", []):
                merged[seed["id"]] = seed

        shard_dir = self.events_dir / "seeds"
        if shard_dir.is_dir():
            for path in sorted(shard_dir.glob("*.json")):
                for seed in load_json(path).get("seeds", []):
                    merged[seed["id"]] = seed

        self._seeds_cache = merged
        return self._seeds_cache

    def get_event_seed(self, seed_id: str) -> dict[str, Any] | None:
        return self.load_event_seeds().get(seed_id)

    def pending_event_seeds(self, seed_ids: list[str]) -> list[dict[str, Any]]:
        catalog = self.load_event_seeds()
        return [catalog[sid] for sid in seed_ids if sid in catalog]

    def load_location_lore(self, location: str) -> str:
        """Match location string to lore/locations/*.md (best effort)."""
        loc_dir = self.lore_dir / "locations"
        if not loc_dir.exists():
            return ""

        location_lower = location.lower()
        for path in sorted(loc_dir.glob("*.md")):
            if path.stem in location_lower or path.stem.replace("_", " ") in location_lower:
                return load_text(path)
            if "애쉬포인트" in location and path.stem == "ashpoint":
                return load_text(path)
            if "ashpoint" in location_lower and path.stem == "ashpoint":
                return load_text(path)
            if ("관측" in location or "tower" in location_lower or "석탑" in location) and path.stem == "observation_tower":
                return load_text(path)
            if ("숲" in location or "forest" in location_lower) and path.stem == "northern_forest":
                return load_text(path)

        # Default: ashpoint for Silverwood frontier start
        fallback = loc_dir / "ashpoint.md"
        if fallback.exists() and ("실버우드" in location or "애쉬" in location):
            return load_text(fallback)
        return ""

    def load_npc_lore(self, npc_ids: list[str] | None = None) -> str:
        """Return relevant NPC sections from lore/npcs.md."""
        path = self.lore_dir / "npcs.md"
        if not path.exists():
            return ""
        full = load_text(path)
        if not npc_ids:
            return full

        id_to_heading = {
            "torren_blacksmith": "토렌",
            "lilian_innkeeper": "릴리안",
            "grey_cloak": "회색 망토",
            "elder_maren": "마렌",
            "child_lysa": "리사",
            "merchant_finn": "핀",
            "silver_stalker": "실버",
        }
        sections: list[str] = []
        for nid in npc_ids:
            heading_key = id_to_heading.get(nid, nid)
            pattern = rf"(## {re.escape(heading_key)}[^\n]*\n(?:.*?\n(?=## |\Z)))"
            match = re.search(pattern, full, re.DOTALL)
            if match:
                sections.append(match.group(1).strip())
        return "\n\n".join(sections) if sections else full

    def build_narrative_context(
        self,
        state: dict[str, Any],
        *,
        max_event_seeds: int = 3,
    ) -> dict[str, Any]:
        """Compact lore bundle for LLM snapshot — loaded on demand, not persisted."""
        world = state.get("world", {})
        location = world.get("location", "")
        flags = state.get("flags", {})

        pending_ids = list(flags.get("pending_events", []))[:max_event_seeds]
        npc_ids = [
            nid
            for nid, loc in state.get("npc_locations", {}).items()
            if location and (location.split("—")[0].strip() in loc or "애쉬" in loc)
        ]
        if not npc_ids:
            npc_ids = [
                "torren_blacksmith",
                "lilian_innkeeper",
                "grey_cloak",
                "elder_maren",
                "child_lysa",
            ]

        seeds = self.pending_event_seeds(pending_ids)
        active_quest = self.get_active_quest(state)
        quest_ctx = None
        if active_quest:
            stage = int(flags.get("quests", {}).get("stage", 1))
            stages = active_quest.get("stages", [])
            if stage <= len(stages):
                quest_ctx = {
                    "id": active_quest["id"],
                    "title": active_quest["title"],
                    "stage": stage,
                    "goal": stages[stage - 1]["goal"],
                    "hint": stages[stage - 1].get("hint", ""),
                }

        return {
            "location_lore": self.load_location_lore(location),
            "npc_lore": self.load_npc_lore(npc_ids),
            "event_seeds": [
                {
                    "id": s["id"],
                    "title": s["title"],
                    "summary": s["summary"],
                    "hook": s.get("hook", ""),
                    "seed_type": s.get("seed_type"),
                    "related_npc": s.get("related_npc"),
                    "main_plot_link": s.get("main_plot_link"),
                }
                for s in seeds
            ],
            "active_quest": quest_ctx,
            "rumors": world.get("rumors", []),
            "reputation": flags.get("reputation", {}),
            "faction_reputation": flags.get("faction_reputation", {}),
            "main_story": flags.get("main_story"),
        }
