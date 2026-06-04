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

    def load_event_seeds(self) -> dict[str, dict[str, Any]]:
        path = self.events_dir / "seeds.json"
        if not path.exists():
            return {}
        if self._seeds_cache is None:
            data = load_json(path)
            self._seeds_cache = {s["id"]: s for s in data.get("seeds", [])}
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
            npc_ids = ["torren_blacksmith", "lilian_innkeeper", "grey_cloak"]

        seeds = self.pending_event_seeds(pending_ids)
        return {
            "location_lore": self.load_location_lore(location),
            "npc_lore": self.load_npc_lore(npc_ids),
            "event_seeds": [
                {"id": s["id"], "title": s["title"], "summary": s["summary"], "hook": s.get("hook", "")}
                for s in seeds
            ],
            "rumors": world.get("rumors", []),
        }
