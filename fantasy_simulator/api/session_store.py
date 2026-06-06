"""Per-player session directories — isolated state copies for API clients."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from utils.game_session import GameSession
from utils.spatial import godot_pixel_position, position_snapshot
from utils.state_manager import StateManager

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_SESSIONS_ROOT = _PACKAGE_ROOT / "api_sessions"
_COPY_DIRS = ("state", "characters", "rules", "events", "lore", "config", "prompts", "schemas")


def package_root() -> Path:
    return _PACKAGE_ROOT


def sessions_root() -> Path:
    path = _SESSIONS_ROOT
    path.mkdir(parents=True, exist_ok=True)
    return path


def _copy_game_tree(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name in _COPY_DIRS:
        src = _PACKAGE_ROOT / name
        if src.exists():
            target = dest / name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(src, target)


class SessionStore:
    """In-memory index of active GameSession objects with on-disk state."""

    def __init__(self) -> None:
        self._sessions: dict[str, GameSession] = {}

    def create(
        self,
        *,
        seed: int | None = None,
        mode: str = "rule",
        temporal_mode: str = "classic",
    ) -> tuple[str, GameSession]:
        session_id = str(uuid.uuid4())
        path = sessions_root() / session_id
        _copy_game_tree(path)
        session = GameSession.from_root(
            path,
            mode=mode,  # type: ignore[arg-type]
            seed=seed,
            temporal_mode=temporal_mode,  # type: ignore[arg-type]
        )
        meta = session.state.setdefault("meta", {})
        if seed is not None:
            meta["rng_seed"] = int(seed)
        elif "rng_seed" not in meta:
            meta["rng_seed"] = session.rng.randint(0, 2_147_483_647)
        session.manager.save(session.state)
        self._sessions[session_id] = session
        return session_id, session

    def get(self, session_id: str) -> GameSession | None:
        if session_id in self._sessions:
            return self._sessions[session_id]
        path = sessions_root() / session_id
        if not (path / "state").is_dir():
            return None
        import json

        meta_seed: int | None = None
        meta_path = path / "state" / "meta.json"
        if meta_path.is_file():
            with meta_path.open(encoding="utf-8") as f:
                meta_seed = json.load(f).get("rng_seed")
        session = GameSession.from_root(path, mode="rule", seed=meta_seed)
        self._sessions[session_id] = session
        return session

    def delete(self, session_id: str) -> bool:
        self._sessions.pop(session_id, None)
        path = sessions_root() / session_id
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            return True
        return False


def turn_payload(session: GameSession, result: dict[str, Any]) -> dict[str, Any]:
    """Enrich TurnResult for Godot HUD binding."""
    world = session.state.get("world", {})
    flags = session.state.get("flags", {})
    return {
        "api_version": 1,
        "session_id": None,
        **result,
        "world": {
            "day": world.get("day"),
            "time_of_day": world.get("time_of_day"),
            "minute_of_day": world.get("minute_of_day"),
            "location": world.get("location"),
            "tension": world.get("tension"),
            "weather": world.get("weather"),
            "zone_id": world.get("zone_id"),
            "map_id": world.get("map_id"),
        },
        "position": position_snapshot(world),
        "godot_position": godot_pixel_position(world),
        "party": list(session.state.get("party", [])),
        "gold": session.state.get("inventory", {}).get("party_gold", 0),
        "combat_active": bool(session.state.get("combat")),
        "main_story_phase": flags.get("main_story", {}).get("phase"),
    }
