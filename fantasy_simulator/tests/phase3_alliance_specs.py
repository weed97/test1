"""Phase 3 alliance ending specs keyed by Phase 1 choice (A–E)."""

from __future__ import annotations

from typing import Any

PHASE3_ALLIANCE_CLIMAX: dict[str, str] = {
    "ally_village": "phase3_climax_alliance_council",
    "seek_truth": "phase3_climax_alliance_wardens",
    "pursue_power": "phase3_climax_alliance_covenant",
    "exploit_chaos": "phase3_climax_alliance_merchants",
    "stay_neutral": "phase3_climax_alliance_knights",
}

PHASE3_FINAL_BY_PHASE1: dict[str, str] = {
    "ally_village": "final_reinforce",
    "seek_truth": "final_reinforce",
    "pursue_power": "final_break",
    "exploit_chaos": "final_chaos",
    "stay_neutral": "final_reinforce",
}

FINAL_CHOICE_BRANCH: dict[str, dict[str, Any]] = {
    "final_reinforce": {
        "branch_seed": "story_choice_final_reinforce",
        "branch_action": "talk elder maren",
    },
    "final_break": {
        "branch_seed": "story_choice_final_break",
        "branch_action": "investigate forest",
        "branch_tension_min": 55,
    },
    "final_chaos": {
        "branch_seed": "story_choice_final_chaos",
        "branch_action": "explore",
    },
}

ALLIANCE_ROUTE_BY_PHASE1_PHASE3: dict[str, dict[str, Any]] = {
    p1: {
        "phase1_choice": p1,
        "phase2_choice": "path_alliance",
        "final_choice_id": PHASE3_FINAL_BY_PHASE1[p1],
        "climax_seed": PHASE3_ALLIANCE_CLIMAX[p1],
        **FINAL_CHOICE_BRANCH[PHASE3_FINAL_BY_PHASE1[p1]],
        "climax_actions": ["investigate forest"],
        "climax_location": "관측탑",
    }
    for p1 in PHASE3_ALLIANCE_CLIMAX
}
