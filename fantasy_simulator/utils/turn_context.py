"""Turn execution context — bundles dependencies for process_player_action."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from utils.llm_client import LLMClient
from utils.rule_engine import RuleEngine
from utils.state_manager import StateManager

Mode = Literal["rule", "llm", "hybrid"]


@dataclass
class TurnContext:
    """Everything needed to resolve one player action."""

    state: dict[str, Any]
    action: str
    turn: int
    mode: Mode
    manager: StateManager
    rules: RuleEngine
    client: LLMClient | None = None


@dataclass
class TurnResult:
    """Outcome of a full turn (time advance + action)."""

    turn: int
    day: int
    time: str
    mode: Mode
    lines: list[str]
    decision: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn": self.turn,
            "day": self.day,
            "time": self.time,
            "mode": self.mode,
            "lines": self.lines,
            "decision": self.decision,
        }
