"""Player faction reputation — tiers, legacy mapping, and gameplay effects."""

from __future__ import annotations

from typing import Any

from utils.io_helpers import load_json


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


class FactionEngine:
    """Manage player ↔ world faction standing."""

    def __init__(self, base_dir: Any) -> None:
        from pathlib import Path

        self.base_dir = Path(base_dir)
        self._config: dict[str, Any] | None = None

    def load_config(self) -> dict[str, Any]:
        if self._config is None:
            path = self.base_dir / "config" / "factions.json"
            self._config = load_json(path) if path.exists() else {"factions": [], "tiers": []}
        return self._config

    def faction_ids(self) -> list[str]:
        return [f["id"] for f in self.load_config().get("factions", [])]

    def faction_def(self, faction_id: str) -> dict[str, Any] | None:
        for f in self.load_config().get("factions", []):
            if f["id"] == faction_id:
                return f
        return None

    def tier_for_value(self, value: int) -> dict[str, Any]:
        cfg = self.load_config()
        lo, hi = cfg.get("reputation_range", [-100, 100])
        v = _clamp(int(value), lo, hi)
        for tier in cfg.get("tiers", []):
            if tier["min"] <= v <= tier["max"]:
                return tier
        return {"id": "neutral", "label_ko": "중립", "min": -9, "max": 9}

    def get_reputation(self, state: dict[str, Any], faction_id: str) -> int:
        rep = state.setdefault("flags", {}).setdefault("faction_reputation", {})
        if faction_id not in rep:
            self._migrate_legacy(state)
        return int(rep.get(faction_id, 0))

    def all_reputation(self, state: dict[str, Any]) -> dict[str, int]:
        self.ensure_initialized(state)
        return dict(state["flags"]["faction_reputation"])

    def ensure_initialized(self, state: dict[str, Any]) -> None:
        flags = state.setdefault("flags", {})
        if "faction_reputation" not in flags:
            self._migrate_legacy(state)
        rep = flags.setdefault("faction_reputation", {})
        for fid in self.faction_ids():
            rep.setdefault(fid, 0)

    def _migrate_legacy(self, state: dict[str, Any]) -> None:
        """Seed faction_reputation from legacy flags.reputation keys."""
        flags = state.setdefault("flags", {})
        legacy = flags.get("reputation", {})
        cfg = self.load_config()
        mapping = cfg.get("legacy_reputation_keys", {})
        faction_rep: dict[str, int] = dict(flags.get("faction_reputation", {}))

        for legacy_key, faction_id in mapping.items():
            if legacy_key in legacy and faction_id not in faction_rep:
                faction_rep[faction_id] = int(legacy[legacy_key]) - 50

        for fid in self.faction_ids():
            faction_rep.setdefault(fid, 0)

        flags["faction_reputation"] = faction_rep

    def adjust_reputation(
        self,
        state: dict[str, Any],
        faction_id: str,
        delta: int,
        *,
        rival_spill: bool = True,
    ) -> list[str]:
        """Apply delta to faction rep; optionally penalize rivals."""
        self.ensure_initialized(state)
        cfg = self.load_config()
        lo, hi = cfg.get("reputation_range", [-100, 100])
        rep = state["flags"]["faction_reputation"]
        before = int(rep.get(faction_id, 0))
        after = _clamp(before + int(delta), lo, hi)
        rep[faction_id] = after
        lines: list[str] = []

        if after != before:
            tier = self.tier_for_value(after)
            fdef = self.faction_def(faction_id)
            name = fdef["name_ko"] if fdef else faction_id
            lines.append(f"[세력] {name} 평판 {after - before:+d} → {after} ({tier['label_ko']})")

        self._sync_legacy_key(state, faction_id, after)

        if rival_spill and delta > 0:
            fdef = self.faction_def(faction_id)
            for rival_id in (fdef or {}).get("rivals", []):
                rival_before = int(rep.get(rival_id, 0))
                rival_after = _clamp(rival_before - max(1, delta // 4), lo, hi)
                if rival_after != rival_before:
                    rep[rival_id] = rival_after
                    rdef = self.faction_def(rival_id)
                    rname = rdef["name_ko"] if rdef else rival_id
                    lines.append(f"[세력] {rname} 평판 {rival_after - rival_before:+d} (라이벌 반응)")

        return lines

    def _sync_legacy_key(self, state: dict[str, Any], faction_id: str, faction_value: int) -> None:
        cfg = self.load_config()
        mapping = cfg.get("legacy_reputation_keys", {})
        legacy = state.setdefault("flags", {}).setdefault("reputation", {})
        for legacy_key, fid in mapping.items():
            if fid == faction_id:
                legacy[legacy_key] = _clamp(faction_value + 50, 0, 100)

    def apply_reputation_outcome(self, state: dict[str, Any], outcome: dict[str, Any]) -> list[str]:
        """Apply reputation / faction_reputation from event or quest outcomes."""
        lines: list[str] = []
        cfg = self.load_config()
        mapping = cfg.get("legacy_reputation_keys", {})

        for key, delta in (outcome.get("faction_reputation") or {}).items():
            lines.extend(self.adjust_reputation(state, key, int(delta)))

        legacy_rep = state.setdefault("flags", {}).setdefault("reputation", {})
        for key, delta in (outcome.get("reputation") or {}).items():
            if key in mapping:
                lines.extend(self.adjust_reputation(state, mapping[key], int(delta)))
            else:
                legacy_rep[key] = _clamp(int(legacy_rep.get(key, 0)) + int(delta), -100, 100)

        return lines

    def tier_id(self, state: dict[str, Any], faction_id: str) -> str:
        return self.tier_for_value(self.get_reputation(state, faction_id))["id"]

    def tier_effects(self, state: dict[str, Any], faction_id: str) -> dict[str, Any]:
        fdef = self.faction_def(faction_id)
        if not fdef:
            return {}
        tier_id = self.tier_id(state, faction_id)
        return dict(fdef.get("tier_effects", {}).get(tier_id, {}))

    def price_modifier(self, state: dict[str, Any]) -> float:
        """Aggregate trade price modifier from merchant guild + council."""
        mod = 0.0
        for fid in ("merchant_guild", "ashpoint_council"):
            effects = self.tier_effects(state, fid)
            mod += float(effects.get("price_modifier", 0))
        return mod

    def is_zone_blocked(self, state: dict[str, Any], zone_id: str) -> tuple[bool, str | None]:
        for fid in self.faction_ids():
            effects = self.tier_effects(state, fid)
            blocked = effects.get("zone_blocked") or []
            if zone_id in blocked:
                fdef = self.faction_def(fid)
                name = fdef["name_ko"] if fdef else fid
                return True, name
        return False, None

    def unlocked_quests(self, state: dict[str, Any]) -> set[str]:
        unlocked: set[str] = set()
        for fid in self.faction_ids():
            effects = self.tier_effects(state, fid)
            for qid in effects.get("quest_unlock") or []:
                unlocked.add(qid)
        return unlocked

    def meets_faction_requirements(
        self,
        state: dict[str, Any],
        requires_min: dict[str, int] | None,
        requires_max: dict[str, int] | None = None,
    ) -> bool:
        if requires_min:
            for fid, minimum in requires_min.items():
                if self.get_reputation(state, fid) < int(minimum):
                    return False
        if requires_max:
            for fid, maximum in requires_max.items():
                if self.get_reputation(state, fid) > int(maximum):
                    return False
        return True

    def attitude_label(self, state: dict[str, Any], faction_id: str) -> str:
        return self.tier_for_value(self.get_reputation(state, faction_id))["label_ko"]

    def format_summary(self, state: dict[str, Any]) -> list[str]:
        self.ensure_initialized(state)
        lines: list[str] = []
        for fid in self.faction_ids():
            fdef = self.faction_def(fid)
            if not fdef:
                continue
            val = self.get_reputation(state, fid)
            tier = self.tier_for_value(val)
            lines.append(f"  - {fdef['name_ko']}: {val} ({tier['label_ko']})")
        return lines
