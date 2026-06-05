"""Contribution-based world-building permissions and growth goals."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_CONFIG_NAME = "contributor_tiers.json"
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent

_KIND_TO_SCORE_KEY: dict[str, str] = {
    "rumor": "approved_rumor",
    "bark": "approved_dialogue",
    "dialogue": "approved_dialogue",
    "quest_hook": "approved_quest_hook",
    "event_seed": "approved_event_seed",
    "branching_seed": "approved_branching_seed",
    "zone_flavor": "approved_event_seed",
}


@lru_cache(maxsize=1)
def load_tier_config(base_dir: Path | str | None = None) -> dict[str, Any]:
    root = Path(base_dir) if base_dir else _PACKAGE_ROOT
    path = root / "config" / _CONFIG_NAME
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def get_world_building(flags: dict[str, Any]) -> dict[str, Any]:
    wb = flags.setdefault("world_building", {})
    wb.setdefault("contributor_tier", "observer")
    wb.setdefault("contribution_score", 0)
    wb.setdefault("detail_level", 1)
    wb.setdefault("pending_contributions", [])
    wb.setdefault("approved_seeds", [])
    wb.setdefault("completed_goals", [])
    wb.setdefault("permissions_override", [])
    wb.setdefault("workshop_unlocked", False)
    wb.setdefault(
        "stats",
        {"submitted": 0, "approved": 0, "rejected": 0, "endorsements_received": 0},
    )
    return wb


def resolve_tier(score: int, *, base_dir: Path | str | None = None) -> dict[str, Any]:
    """Return tier record for contribution score (highest matching min_score)."""
    cfg = load_tier_config(base_dir)
    tiers = sorted(cfg["tiers"], key=lambda t: t["min_score"])
    chosen = tiers[0]
    for tier in tiers:
        if score >= int(tier["min_score"]):
            chosen = tier
    return chosen


def sync_tier_from_score(
    flags: dict[str, Any], *, base_dir: Path | str | None = None
) -> dict[str, Any]:
    """Update world_building tier fields from contribution_score."""
    wb = get_world_building(flags)
    tier = resolve_tier(int(wb["contribution_score"]), base_dir=base_dir)
    wb["contributor_tier"] = tier["id"]
    wb["detail_level"] = int(tier["detail_level"])
    return tier


def permissions_for_tier(
    tier_id: str, *, base_dir: Path | str | None = None
) -> set[str]:
    cfg = load_tier_config(base_dir)
    for tier in cfg["tiers"]:
        if tier["id"] == tier_id:
            return set(tier.get("permissions", []))
    return set()


def effective_permissions(
    flags: dict[str, Any], *, base_dir: Path | str | None = None
) -> set[str]:
    wb = get_world_building(flags)
    sync_tier_from_score(flags, base_dir=base_dir)
    perms = permissions_for_tier(wb["contributor_tier"], base_dir=base_dir)
    perms.update(wb.get("permissions_override", []))
    for goal_id in wb.get("completed_goals", []):
        for goal in load_tier_config(base_dir).get("growth_goals", []):
            if goal["id"] == goal_id and goal.get("unlock_permission"):
                perms.add(goal["unlock_permission"])
    return perms


def can(
    flags: dict[str, Any],
    permission: str,
    *,
    base_dir: Path | str | None = None,
) -> bool:
    return permission in effective_permissions(flags, base_dir=base_dir)


def seed_limits(
    flags: dict[str, Any], *, base_dir: Path | str | None = None
) -> dict[str, Any]:
    wb = get_world_building(flags)
    tier = resolve_tier(int(wb["contribution_score"]), base_dir=base_dir)
    return dict(tier.get("seed_limits", {}))


def validate_submission(
    flags: dict[str, Any],
    entry: dict[str, Any],
    *,
    base_dir: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Check whether a draft seed fits tier limits and permissions."""
    issues: list[str] = []
    kind = entry.get("kind", "")
    perm_by_kind = {
        "rumor": "submit_rumor",
        "bark": "submit_bark",
        "quest_hook": "submit_quest_hook",
        "event_seed": "submit_event_seed",
        "branching_seed": "submit_branching_seed",
        "zone_flavor": "attach_zone_flavor",
    }
    required_perm = perm_by_kind.get(kind)
    if required_perm and not can(flags, required_perm, base_dir=base_dir):
        issues.append(f"권한 없음: {required_perm} (티어 {get_world_building(flags)['contributor_tier']})")

    limits = seed_limits(flags, base_dir=base_dir)
    if int(entry.get("field_count", 0)) > int(limits.get("max_fields", 0)):
        issues.append(
            f"필드 수 초과: {entry.get('field_count')} > {limits.get('max_fields')}"
        )
    if int(entry.get("dialogue_lines", 0)) > int(limits.get("max_dialogue_lines", 0)):
        issues.append(
            f"대사 줄 수 초과: {entry.get('dialogue_lines')} > {limits.get('max_dialogue_lines')}"
        )
    if int(entry.get("branch_count", 0)) > int(limits.get("max_branches", 0)):
        issues.append(
            f"분기 수 초과: {entry.get('branch_count')} > {limits.get('max_branches')}"
        )
    detail = int(entry.get("detail_level", 1))
    wb = get_world_building(flags)
    if detail > int(wb.get("detail_level", 1)):
        issues.append(
            f"디테일 등급 초과: 요청 {detail} > 허용 {wb.get('detail_level')}"
        )
    return (len(issues) == 0, issues)


def score_for_kind(kind: str, *, base_dir: Path | str | None = None) -> int:
    cfg = load_tier_config(base_dir)
    key = _KIND_TO_SCORE_KEY.get(kind, "approved_rumor")
    return int(cfg["score_sources"].get(key, 0))


def award_contribution(
    flags: dict[str, Any],
    entry: dict[str, Any],
    *,
    approved: bool = False,
    quality_score: float = 1.0,
    base_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Record submission; on approve, add score and re-sync tier."""
    wb = get_world_building(flags)
    stats = wb["stats"]
    entry = dict(entry)
    entry.setdefault("status", "pending")
    entry.setdefault("quality_score", quality_score)

    ok, issues = validate_submission(flags, entry, base_dir=base_dir)
    if not ok:
        entry["status"] = "rejected"
        entry["reject_reasons"] = issues
        stats["rejected"] = int(stats.get("rejected", 0)) + 1
        wb["pending_contributions"].append(entry)
        return entry

    stats["submitted"] = int(stats.get("submitted", 0)) + 1
    if not approved:
        wb["pending_contributions"].append(entry)
        return entry

    cfg = load_tier_config(base_dir)
    base = score_for_kind(str(entry.get("kind", "rumor")), base_dir=base_dir)
    bonus = int(
        round(
            float(cfg["score_sources"].get("arbiter_quality_bonus_max", 0))
            * max(0.0, min(1.0, quality_score))
        )
    )
    awarded = base + bonus
    entry["status"] = "approved"
    entry["score_awarded"] = awarded
    wb["contribution_score"] = int(wb["contribution_score"]) + awarded
    wb["approved_seeds"].append(entry)
    stats["approved"] = int(stats.get("approved", 0)) + 1
    sync_tier_from_score(flags, base_dir=base_dir)
    evaluate_growth_goals(flags, base_dir=base_dir)
    return entry


def _goal_satisfied(
    wb: dict[str, Any], goal: dict[str, Any], *, base_dir: Path | str | None
) -> bool:
    check = goal.get("check", {})
    ctype = check.get("type")
    if ctype == "flag":
        path = check.get("path", "")
        if path == "world_building.workshop_unlocked":
            return bool(wb.get("workshop_unlocked"))
        return False
    if ctype == "score_at_least":
        return int(wb.get("contribution_score", 0)) >= int(check.get("min_score", 0))
    if ctype == "approved_count":
        kind = check.get("kind", "")
        need = int(check.get("min", 1))
        count = sum(1 for s in wb.get("approved_seeds", []) if s.get("kind") == kind)
        return count >= need
    if ctype == "seed_detail":
        need_lines = int(check.get("min_dialogue_lines", 0))
        return any(
            int(s.get("dialogue_lines", 0)) >= need_lines
            for s in wb.get("approved_seeds", [])
        )
    return False


def evaluate_growth_goals(
    flags: dict[str, Any], *, base_dir: Path | str | None = None
) -> list[dict[str, Any]]:
    """Complete eligible growth goals and apply rewards."""
    wb = get_world_building(flags)
    completed: list[dict[str, Any]] = []
    done_ids = set(wb.get("completed_goals", []))
    cfg = load_tier_config(base_dir)

    for goal in cfg.get("growth_goals", []):
        gid = goal["id"]
        if gid in done_ids:
            continue
        if not _goal_satisfied(wb, goal, base_dir=base_dir):
            continue
        reward = int(goal.get("reward_score", 0))
        wb["contribution_score"] = int(wb["contribution_score"]) + reward
        done_ids.add(gid)
        unlock = goal.get("unlock_permission")
        if unlock:
            overrides = wb.setdefault("permissions_override", [])
            if unlock not in overrides:
                overrides.append(unlock)
        completed.append(goal)

    wb["completed_goals"] = sorted(done_ids)
    sync_tier_from_score(flags, base_dir=base_dir)
    return completed


def next_growth_goal(
    flags: dict[str, Any], *, base_dir: Path | str | None = None
) -> dict[str, Any] | None:
    """First incomplete growth goal (progression hint for UI)."""
    wb = get_world_building(flags)
    done_ids = set(wb.get("completed_goals", []))
    for goal in load_tier_config(base_dir).get("growth_goals", []):
        if goal["id"] not in done_ids:
            return goal
    return None


def tier_progress(
    flags: dict[str, Any], *, base_dir: Path | str | None = None
) -> dict[str, Any]:
    """Score progress toward next tier (for HUD / workshop UI)."""
    wb = get_world_building(flags)
    score = int(wb["contribution_score"])
    cfg = load_tier_config(base_dir)
    tiers = sorted(cfg["tiers"], key=lambda t: t["min_score"])
    current = resolve_tier(score, base_dir=base_dir)
    idx = next(i for i, t in enumerate(tiers) if t["id"] == current["id"])
    if idx + 1 < len(tiers):
        nxt = tiers[idx + 1]
        span = int(nxt["min_score"]) - int(current["min_score"])
        into = score - int(current["min_score"])
        pct = 0.0 if span <= 0 else min(1.0, into / span)
        return {
            "current_tier": current["id"],
            "current_label": current.get("label", current["id"]),
            "next_tier": nxt["id"],
            "next_label": nxt.get("label", nxt["id"]),
            "score": score,
            "next_min_score": int(nxt["min_score"]),
            "progress_fraction": pct,
        }
    return {
        "current_tier": current["id"],
        "current_label": current.get("label", current["id"]),
        "next_tier": None,
        "next_label": None,
        "score": score,
        "next_min_score": None,
        "progress_fraction": 1.0,
    }
