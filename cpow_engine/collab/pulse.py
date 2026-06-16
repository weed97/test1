"""빌드 펄스 — 협동 창조를 모아서 함께 반영."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from cpow_engine.collab.noise_gate import ChangeVerdict
from cpow_engine.models import CreativeObject, WorldDelta
from cpow_engine.cpow import CPoWScore


@dataclass
class PendingCreation:
    creator_id: str
    obj: CreativeObject
    creativity_score: float = 1.0
    queued_at: float = field(default_factory=time.monotonic)


@dataclass
class PulseResult:
    advanced: bool
    pulse_number: int
    applied_count: int = 0
    results: list["AppliedCreationResult"] = field(default_factory=list)
    delta: WorldDelta | None = None
    score: CPoWScore | None = None
    reason: str = ""
    seconds_until_next: float = 0.0


@dataclass
class AppliedCreationResult:
    ok: bool
    creator_id: str
    object_id: str = ""
    verdict: ChangeVerdict | None = None
    reason: str = ""


@dataclass
class QueueResult:
    ok: bool
    object_id: str = ""
    queued: bool = False
    pulse_number: int = 0
    pending_count: int = 0
    contributors_in_pulse: int = 0
    seconds_until_pulse: float = 0.0
    cooldown_remaining: float = 0.0
    reason: str = ""
