"""Lightweight logging: a human-readable transcript plus a JSONL event stream.

The simulation writes two artefacts to ``logs/``:
* ``transcript.log`` — the readable story / console mirror,
* ``events.jsonl``  — structured events (one JSON object per line) for analysis.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any


def get_logger(logs_dir: str, name: str = "fantasy_sim") -> "SimLogger":
    os.makedirs(logs_dir, exist_ok=True)
    return SimLogger(logs_dir, name)


class SimLogger:
    def __init__(self, logs_dir: str, name: str) -> None:
        self.logs_dir = logs_dir
        self.transcript_path = os.path.join(logs_dir, "transcript.log")
        self.events_path = os.path.join(logs_dir, "events.jsonl")
        self._py = logging.getLogger(name)
        if not self._py.handlers:
            self._py.setLevel(logging.INFO)
            handler = logging.FileHandler(self.transcript_path, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            self._py.addHandler(handler)

    def line(self, text: str, echo: bool = True) -> None:
        self._py.info(text)
        if echo:
            print(text)

    def event(self, kind: str, **fields: Any) -> None:
        record = {"ts": time.time(), "kind": kind, **fields}
        with open(self.events_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def section(self, title: str, echo: bool = True) -> None:
        bar = "=" * max(8, len(title) + 4)
        self.line(f"\n{bar}\n  {title}\n{bar}", echo=echo)
