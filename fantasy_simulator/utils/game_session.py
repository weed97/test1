"""Game session — turn controller (state + engines, no action logic)."""

from __future__ import annotations

import copy
import random
from pathlib import Path
from typing import Any, Optional

from utils.content_loader import ContentLoader
from utils.event_engine import EventEngine
from utils.llm_client import LLMClient
from utils.rule_engine import RuleEngine
from utils.state_loader import StateLoader, event_entries
from utils.state_manager import StateManager
from utils.turn_context import Mode, TurnContext, TurnResult
from utils.turn_processor import execute_turn


class GameSession:
    """Lightweight turn controller. Action logic lives in turn_processor."""

    def __init__(
        self,
        manager: StateManager,
        state: dict[str, Any],
        *,
        mode: Mode = "rule",
        rng: random.Random | None = None,
        seed: int | None = None,
        client: LLMClient | None = None,
    ) -> None:
        self.manager = manager
        self.loader = manager.loader
        self.mode = mode
        self.state = state
        self.rng = rng or random.Random(seed)
        self.content = ContentLoader(manager.base_dir)
        self.event_engine = EventEngine(self.content, self.rng)
        self.rules = RuleEngine(self.state, self.rng, event_engine=self.event_engine)
        self.turn = len(event_entries(self.state))
        if client is not None:
            self.client = client
        elif mode in ("llm", "hybrid"):
            self.client = LLMClient(manager.base_dir)
        else:
            self.client = None

    @classmethod
    def from_root(
        cls,
        root: Path | str,
        *,
        mode: Mode = "rule",
        seed: int | None = None,
    ) -> GameSession:
        loader = StateLoader.from_package_root(root)
        manager = StateManager(loader.base_dir, store=loader.store)
        state = manager.load()
        return cls(manager, state, mode=mode, seed=seed)

    @classmethod
    def from_loader(
        cls,
        loader: StateLoader,
        *,
        mode: Mode = "rule",
        seed: int | None = None,
    ) -> GameSession:
        manager = StateManager(loader.base_dir, store=loader.store)
        state = manager.load()
        return cls(manager, state, mode=mode, seed=seed)

    def ctx(self, action: str, turn: int | None = None) -> TurnContext:
        return TurnContext(
            state=self.state,
            action=action,
            turn=turn if turn is not None else self.turn,
            mode=self.mode,
            manager=self.manager,
            rules=self.rules,
            client=self.client,
        )

    def run_turn(self, action: str = "explore", *, enemy_id: str | None = None) -> dict[str, Any]:
        """Advance one turn. Delegates to turn_processor.execute_turn()."""
        self.turn += 1
        result = execute_turn(
            self.ctx(action, turn=self.turn),
            loader=self.loader,
            enemy_id=enemy_id,
        )
        self.manager.refresh_state(self.state)
        return result.to_dict()

    def start_combat(self, enemy_id: str) -> None:
        enemy = copy.deepcopy(self.loader.load_character(enemy_id))
        party = [copy.deepcopy(c) for c in self.loader.load_party(self.state)]
        self.rules.start_combat(enemy, party, self.turn)
        self.manager.append_event(
            {"turn": self.turn, "type": "combat_start", "summary": f"전투 시작: {enemy['name']}"},
            self.state,
        )
        self.manager.save(self.state)

    def status_report(self) -> str:
        return self.manager.format_status_report(
            self.state,
            event_engine=self.event_engine,
            mode=self.mode,
        )

    def save(self) -> None:
        self.manager.save(self.state)


# Backward-compatible alias
SimulationEngine = GameSession
