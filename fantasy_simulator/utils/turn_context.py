"""Turn execution context — bundles dependencies for process_player_action."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from utils.llm_client import LLMClient
from utils.rule_engine import RuleEngine
from utils.state_manager import StateManager
from utils.temporal import TemporalMode

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
    temporal_mode: TemporalMode = "classic"
    time_scale: float = 1.0
    include_presence: bool = False


@dataclass
class TurnResult:
    """Outcome of a full turn (time advance + action)."""

    turn: int
    day: int
    time: str
    mode: Mode
    lines: list[str]
    decision: dict[str, Any] | None = None
    moment_kind: str | None = None
    time_steps: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn": self.turn,
            "day": self.day,
            "time": self.time,
            "mode": self.mode,
            "lines": self.lines,
            "decision": self.decision,
            "moment_kind": self.moment_kind,
            "time_steps": self.time_steps,
        }
