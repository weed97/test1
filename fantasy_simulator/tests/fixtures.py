"""Shared test fixtures — isolated copy of game data for unit tests."""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

PACKAGE_ROOT = Path(__file__).resolve().parent.parent

_COPY_DIRS = ("state", "characters", "rules", "events", "lore", "config", "prompts")


def copy_game_root() -> Path:
    """Copy minimal game tree into a fresh temp directory."""
    tmp = Path(tempfile.mkdtemp(prefix="fantasy_sim_"))
    for name in _COPY_DIRS:
        src = PACKAGE_ROOT / name
        if src.exists():
            shutil.copytree(src, tmp / name)
    return tmp


@contextmanager
def isolated_game_root() -> Iterator[Path]:
    """Temp game root, deleted on exit."""
    root = copy_game_root()
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)
