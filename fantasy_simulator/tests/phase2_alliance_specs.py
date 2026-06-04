"""Phase 2 alliance branch specs keyed by Phase 1 choice (A–E)."""

from __future__ import annotations

from typing import Any

ALLIANCE_BRANCH_SEEDS: tuple[str, ...] = (
    "story_alliance_council",
    "story_alliance_wardens",
    "story_alliance_covenant",
    "story_alliance_merchants",
    "story_alliance_knights",
)

ALLIANCE_ROUTE_BY_PHASE1: dict[str, dict[str, Any]] = {
    "ally_village": {
        "phase1_choice": "ally_village",
        "branch_seed": "story_alliance_council",
        "branch_action": "talk elder maren",
        "climax_seed": "phase2_climax_alliance_council",
        "climax_actions": ["explore forest"],
        "climax_location": "ashpoint",
        "alliance_faction": "ashpoint_council",
    },
    "seek_truth": {
        "phase1_choice": "seek_truth",
        "branch_seed": "story_alliance_wardens",
        "branch_action": "talk grey cloak",
        "climax_seed": "phase2_climax_alliance_wardens",
        "climax_actions": ["investigate forest"],
        "climax_location": "북쪽 숲 — 연기가 보이는 외곽",
        "alliance_faction": "ashen_wardens",
    },
    "pursue_power": {
        "phase1_choice": "pursue_power",
        "branch_seed": "story_alliance_covenant",
        "branch_action": "explore",
        "branch_time": "night",
        "climax_seed": "phase2_climax_alliance_covenant",
        "climax_actions": ["investigate forest"],
        "climax_location": "북쪽 숲 — 연기가 보이는 외곽",
        "alliance_faction": "black_covenant",
    },
    "exploit_chaos": {
        "phase1_choice": "exploit_chaos",
        "branch_seed": "story_alliance_merchants",
        "branch_action": "talk lilian",
        "climax_seed": "phase2_climax_alliance_merchants",
        "climax_actions": ["explore forest"],
        "climax_location": "ashpoint",
        "alliance_faction": "silverwood_trade_union",
    },
    "stay_neutral": {
        "phase1_choice": "stay_neutral",
        "branch_seed": "story_alliance_knights",
        "branch_action": "explore",
        "climax_seed": "phase2_climax_alliance_knights",
        "climax_actions": ["explore forest"],
        "climax_location": "ashpoint",
        "alliance_faction": "silver_cross_order",
    },
}
