"""JSON and text file I/O helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path | str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path | str, data: Any, *, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=indent)


def load_text(path: Path | str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()
