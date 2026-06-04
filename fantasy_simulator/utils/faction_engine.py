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
        resolved = self._resolve_faction_id(faction_id)
        for f in self.load_config().get("factions", []):
            if f["id"] == resolved:
                return f
        return None

    def _resolve_faction_id(self, faction_id: str) -> str:
        return self.load_config().get("legacy_faction_ids", {}).get(faction_id, faction_id)

    def tier_for_value(self, value: int) -> dict[str, Any]:
        cfg = self.load_config()
        lo, hi = cfg.get("reputation_range", [-100, 100])
        v = _clamp(int(value), lo, hi)
        for tier in cfg.get("tiers", []):
            if tier["min"] <= v <= tier["max"]:
                return tier
        return {"id": "neutral", "label_ko": "중립", "min": -9, "max": 9}

    def get_reputation(self, state: dict[str, Any], faction_id: str) -> int:
        self.ensure_initialized(state)
        fid = self._resolve_faction_id(faction_id)
        return int(state["flags"]["faction_reputation"].get(fid, 0))

    def all_reputation(self, state: dict[str, Any]) -> dict[str, int]:
        self.ensure_initialized(state)
        return dict(state["flags"]["faction_reputation"])

    def ensure_initialized(self, state: dict[str, Any]) -> None:
        flags = state.setdefault("flags", {})
        self._migrate_faction_ids(flags)
        if "faction_reputation" not in flags or not flags.get("faction_reputation"):
            self._migrate_legacy(state)
        rep = flags.setdefault("faction_reputation", {})
        for fid in self.faction_ids():
            rep.setdefault(fid, 0)
        self._sync_player_factions_mirror(state)

    def _migrate_faction_ids(self, flags: dict[str, Any]) -> None:
        """Rename deprecated faction IDs in saved state."""
        cfg = self.load_config()
        mapping = cfg.get("legacy_faction_ids", {})
        rep = flags.get("faction_reputation")
        if not rep:
            return
        for old_id, new_id in mapping.items():
            if old_id in rep and new_id not in rep:
                rep[new_id] = rep.pop(old_id)
            elif old_id in rep:
                rep.pop(old_id, None)
        if "ash_church" in rep:
            rep.pop("ash_church", None)

    def _migrate_legacy(self, state: dict[str, Any]) -> None:
        """Seed faction_reputation from legacy flags.reputation keys."""
        flags = state.setdefault("flags", {})
        legacy = flags.get("reputation", {})
        cfg = self.load_config()
        mapping = cfg.get("legacy_reputation_keys", {})
        faction_rep: dict[str, int] = dict(flags.get("faction_reputation", {}))
        self._migrate_faction_ids(flags)

        for legacy_key, faction_id in mapping.items():
            fid = self._resolve_faction_id(faction_id)
            if legacy_key in legacy and fid not in faction_rep:
                faction_rep[fid] = int(legacy[legacy_key]) - 50

        for fid in self.faction_ids():
            faction_rep.setdefault(fid, 0)

        flags["faction_reputation"] = faction_rep

    def _sync_player_factions_mirror(self, state: dict[str, Any]) -> None:
        """Mirror player rep into state.factions for world_state.json readability."""
        rep = state.get("flags", {}).get("faction_reputation", {})
        if not rep:
            return
        factions = state.setdefault("factions", {})
        player = factions.setdefault("player_reputation", {})
        for fid in self.faction_ids():
            fdef = self.faction_def(fid)
            if not fdef:
                continue
            val = int(rep.get(fid, 0))
            tier = self.tier_for_value(val)
            player[fid] = {
                "name_ko": fdef["name_ko"],
                "value": val,
                "tier": tier["id"],
                "tier_label_ko": tier["label_ko"],
            }

    def adjust_reputation(
        self,
        state: dict[str, Any],
        faction_id: str,
        delta: int,
        *,
        relationship_spill: bool = True,
    ) -> list[str]:
        """Apply delta to faction rep; propagate via relationship matrix."""
        self.ensure_initialized(state)
        cfg = self.load_config()
        lo, hi = cfg.get("reputation_range", [-100, 100])
        fid = self._resolve_faction_id(faction_id)
        rep = state["flags"]["faction_reputation"]
        before = int(rep.get(fid, 0))
        after = _clamp(before + int(delta), lo, hi)
        rep[fid] = after
        lines: list[str] = []

        if after != before:
            tier = self.tier_for_value(after)
            fdef = self.faction_def(fid)
            name = fdef["name_ko"] if fdef else fid
            lines.append(f"[세력] {name} 평판 {after - before:+d} → {after} ({tier['label_ko']})")
            lines.extend(self._check_milestones(state, fid, before, after))

        self._sync_legacy_key(state, fid, after)

        if relationship_spill and delta > 0:
            lines.extend(self._apply_relationship_spill(state, fid, int(delta), lo, hi))

        self._sync_player_factions_mirror(state)
        return lines

    def _apply_relationship_spill(
        self,
        state: dict[str, Any],
        source_id: str,
        delta: int,
        lo: int,
        hi: int,
    ) -> list[str]:
        lines: list[str] = []
        cfg = self.load_config()
        stance_rules = cfg.get("relationship_stances", {})
        fdef = self.faction_def(source_id)
        if not fdef:
            return lines
        rep = state["flags"]["faction_reputation"]

        for target_id, stance in (fdef.get("relationships") or {}).items():
            target_id = self._resolve_faction_id(target_id)
            rule = stance_rules.get(stance, {})
            effect = rule.get("on_other_gain", "none")
            magnitude = float(rule.get("magnitude", 0.25))
            if effect == "none":
                continue

            change = 0
            if effect == "penalty":
                change = -max(1, int(delta * magnitude))
            elif effect == "bonus":
                change = max(1, int(delta * magnitude))
            elif effect == "mutual":
                change = max(1, int(delta * magnitude))

            if not change:
                continue
            before = int(rep.get(target_id, 0))
            after = _clamp(before + change, lo, hi)
            if after == before:
                continue
            rep[target_id] = after
            tdef = self.faction_def(target_id)
            tname = tdef["name_ko"] if tdef else target_id
            label = {"penalty": "관계 악화", "bonus": "동맹 반응", "mutual": "이해관계"}.get(effect, "반응")
            lines.append(f"[세력] {tname} 평판 {after - before:+d} ({label})")

        return lines

    def _check_milestones(
        self,
        state: dict[str, Any],
        faction_id: str,
        before: int,
        after: int,
    ) -> list[str]:
        fdef = self.faction_def(faction_id)
        if not fdef:
            return []
        milestones = fdef.get("reputation_milestones", {})
        lines: list[str] = []
        triggered = state.setdefault("flags", {}).setdefault("faction_milestones_hit", [])

        for threshold_str, meta in milestones.items():
            threshold = int(threshold_str)
            key = f"{faction_id}:{threshold}"
            if key in triggered:
                continue
            crossed_up = before < threshold <= after
            crossed_down = before > threshold >= after
            if not (crossed_up or crossed_down):
                continue
            triggered.append(key)
            event_id = meta.get("pending_event")
            if event_id:
                pending = state.setdefault("flags", {}).setdefault("pending_events", [])
                if event_id not in pending:
                    pending.append(event_id)
            summary = meta.get("summary")
            if summary:
                lines.append(f"[세력 이벤트] {summary}")
        return lines

    def _sync_legacy_key(self, state: dict[str, Any], faction_id: str, faction_value: int) -> None:
        cfg = self.load_config()
        mapping = cfg.get("legacy_reputation_keys", {})
        legacy = state.setdefault("flags", {}).setdefault("reputation", {})
        for legacy_key, fid in mapping.items():
            if self._resolve_faction_id(fid) == faction_id:
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
        """Aggregate trade price modifier from trade union + council."""
        mod = 0.0
        for fid in ("silverwood_trade_union", "ashpoint_council"):
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

    def relationship_stance(self, from_id: str, to_id: str) -> str:
        fdef = self.faction_def(from_id)
        if not fdef:
            return "neutral"
        return fdef.get("relationships", {}).get(self._resolve_faction_id(to_id), "neutral")
