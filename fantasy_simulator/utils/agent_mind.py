"""Shim — implementation lives in utils.ecology.agent_mind."""

from utils.ecology.agent_mind import (  # noqa: F401
    agent_plan_priority,
    commit_skill_costs,
    count_nearby_threats,
    decay_skill_cooldowns,
    execute_agent_plan_sequential,
    plan_agent_action,
    preview_skill_damage,
    tick_agent_mind,
    update_relations,
    use_skill,
)

__all__ = [
    "agent_plan_priority",
    "commit_skill_costs",
    "count_nearby_threats",
    "decay_skill_cooldowns",
    "execute_agent_plan_sequential",
    "plan_agent_action",
    "preview_skill_damage",
    "tick_agent_mind",
    "update_relations",
    "use_skill",
]
