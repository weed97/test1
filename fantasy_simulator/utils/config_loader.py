"""Cached JSON config loading for simulation modules."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from utils.io_helpers import load_json


@lru_cache(maxsize=128)
def _cached_load(abs_path: str) -> Any:
    return load_json(abs_path)


def config_path(base_dir: str | Path, filename: str) -> Path:
    return Path(base_dir).resolve() / "config" / filename


def load_config(base_dir: str | Path, filename: str) -> dict[str, Any]:
    path = str(config_path(base_dir, filename))
    data = _cached_load(path)
    if not isinstance(data, dict):
        raise TypeError(f"Expected object JSON in config/{filename}")
    return data
