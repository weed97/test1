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
from utils.state_loader import StateLoader
from utils.state_manager import StateManager
from utils.main_story_engine import _advance_turn_counter, _current_turn
from utils.turn_context import Mode, TurnContext, TurnResult
from utils.temporal import TemporalMode
from utils.spatial import ensure_world_position, sync_position
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
        temporal_mode: TemporalMode = "classic",
    ) -> None:
        self.manager = manager
        self.loader = manager.loader
        self.mode = mode
        self.state = state
        self.rng = rng or random.Random(seed)
        self.default_temporal_mode: TemporalMode = temporal_mode
        self.content = ContentLoader(manager.base_dir)
        self.event_engine = EventEngine(self.content, self.rng)
        self.rules = RuleEngine(self.state, self.rng, event_engine=self.event_engine)
        ensure_world_position(self.state["world"], base_dir=self.manager.base_dir)
        self.turn = _current_turn(self.state) - 1
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
        temporal_mode: TemporalMode = "classic",
    ) -> GameSession:
        loader = StateLoader.from_package_root(root)
        manager = StateManager(loader.base_dir, store=loader.store)
        state = manager.load()
        return cls(manager, state, mode=mode, seed=seed, temporal_mode=temporal_mode)

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

    def ctx(
        self,
        action: str,
        turn: int | None = None,
        *,
        temporal_mode: TemporalMode | None = None,
        time_scale: float | None = None,
        include_presence: bool | None = None,
    ) -> TurnContext:
        mode = temporal_mode if temporal_mode is not None else getattr(
            self, "_temporal_mode", "classic"
        )
        scale = time_scale if time_scale is not None else getattr(self, "_time_scale", 1.0)
        presence = include_presence if include_presence is not None else getattr(
            self, "_include_presence", mode in ("nex", "precision")
        )
        return TurnContext(
            state=self.state,
            action=action,
            turn=turn if turn is not None else self.turn,
            mode=self.mode,
            manager=self.manager,
            rules=self.rules,
            client=self.client,
            temporal_mode=mode,
            time_scale=scale,
            include_presence=presence,
        )

    def apply_position(
        self,
        *,
        map_id: str,
        x: int,
        y: int,
        facing: str = "south",
        allow_map_transition: bool = True,
    ) -> dict[str, Any]:
        """Sync Godot tile coords into world state (no turn advance)."""
        ensure_world_position(self.state["world"], base_dir=self.manager.base_dir)
        meta = sync_position(
            self.state,
            map_id=map_id,
            x=x,
            y=y,
            facing=facing,
            base_dir=self.manager.base_dir,
            allow_map_transition=allow_map_transition,
        )
        if meta.get("ok"):
            self.manager.save(self.state)
        return meta

    def run_turn(
        self,
        action: str = "explore",
        *,
        enemy_id: str | None = None,
        temporal_mode: TemporalMode | None = None,
        time_scale: float = 1.0,
        include_presence: bool | None = None,
        position: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Advance one simulation beat (Classic turn or Nex moment)."""
        if position:
            self.apply_position(
                map_id=str(position["map_id"]),
                x=int(position["x"]),
                y=int(position["y"]),
                facing=str(position.get("facing", "south")),
                allow_map_transition=position.get("allow_map_transition", True),
            )
        if temporal_mode is None:
            temporal_mode = self.default_temporal_mode
        self._temporal_mode = temporal_mode
        self._time_scale = time_scale
        self._include_presence = include_presence if include_presence is not None else (
            temporal_mode in ("nex", "precision")
        )
        turn = _current_turn(self.state)
        result = execute_turn(
            self.ctx(
                action,
                turn=turn,
                temporal_mode=temporal_mode,
                time_scale=time_scale,
                include_presence=self._include_presence,
            ),
            loader=self.loader,
            enemy_id=enemy_id,
        )
        _advance_turn_counter(self.state, turn)
        self.turn = turn
        self.manager.save(self.state)
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
