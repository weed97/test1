"""시행된 시스템 — 런타임 규칙 집행."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from cpow_engine.areas.governance import EnactedSystem, SystemProposalKind
from cpow_engine.collab.policy import CollabPolicy


@dataclass
class RuntimeRules:
    """여러 시행 시스템을 병합한 실효 규칙."""

    min_creator_cooldown_sec: float | None = None
    max_creations_per_creator_per_pulse: int | None = None
    max_creations_per_tick: int | None = None
    creations_per_window: int | None = None
    creation_window_sec: float | None = None
    destroy_penalty_multiplier: float = 1.0
    max_destroys_per_window: int | None = None
    destroy_window_sec: float | None = None
    cross_destroy_scale: float = 1.0
    governance_approval_ratio: float | None = None
    npc_creations_per_window: int | None = None
    npc_window_sec: float | None = None
    block_npc_creation: bool = False

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class RuntimeCheckResult:
    ok: bool
    reason: str = ""
    rule_source: str = ""


class SystemRuntime:
    """거버넌스로 시행된 시스템을 실제 창조·파괴·NPC에 적용."""

    def __init__(
        self,
        *,
        on_register: Callable[[EnactedSystem], None] | None = None,
    ) -> None:
        self._enacted: list[EnactedSystem] = []
        self._creation_ts: dict[str, list[float]] = {}
        self._destroy_ts: dict[str, list[float]] = {}
        self._npc_creation_ts: dict[str, list[float]] = {}
        self._on_register = on_register

    def register(self, system: EnactedSystem) -> None:
        self._enacted.append(system)
        if self._on_register:
            self._on_register(system)

    def enacted_systems(self) -> list[dict]:
        return [s.to_dict() for s in self._enacted]

    def merged_rules(self) -> RuntimeRules:
        rules = RuntimeRules()
        for system in self._enacted:
            self._merge_spec(rules, system)
        return rules

    def apply_collab_policy(self, base: CollabPolicy) -> CollabPolicy:
        rules = self.merged_rules()
        data = base.to_dict()
        if rules.min_creator_cooldown_sec is not None:
            data["min_creator_cooldown_sec"] = max(
                float(data["min_creator_cooldown_sec"]),
                rules.min_creator_cooldown_sec,
            )
        if rules.max_creations_per_creator_per_pulse is not None:
            data["max_creations_per_creator_per_pulse"] = min(
                int(data["max_creations_per_creator_per_pulse"]),
                rules.max_creations_per_creator_per_pulse,
            )
        if rules.max_creations_per_tick is not None:
            data["max_creations_per_tick"] = min(
                int(data["max_creations_per_tick"]),
                rules.max_creations_per_tick,
            )
        return CollabPolicy(
            max_relative_change=float(data["max_relative_change"]),
            max_absolute_heat_delta=float(data["max_absolute_heat_delta"]),
            max_creations_per_tick=int(data["max_creations_per_tick"]),
            max_patches_per_batch=int(data["max_patches_per_batch"]),
            damp_factor=float(data["damp_factor"]),
            noise_threshold=float(data["noise_threshold"]),
            min_creativity_for_large_change=float(
                data["min_creativity_for_large_change"]
            ),
            large_change_multiplier=float(data["large_change_multiplier"]),
            pulse_interval_sec=float(data["pulse_interval_sec"]),
            min_creator_cooldown_sec=float(data["min_creator_cooldown_sec"]),
            max_creations_per_creator_per_pulse=int(
                data["max_creations_per_creator_per_pulse"]
            ),
        )

    def governance_approval_ratio(self, default: float) -> float:
        rules = self.merged_rules()
        if rules.governance_approval_ratio is not None:
            return max(default, rules.governance_approval_ratio)
        return default

    def check_creation_allowed(
        self,
        user_id: str,
        *,
        now: float | None = None,
    ) -> RuntimeCheckResult:
        rules = self.merged_rules()
        if rules.creations_per_window is None or rules.creation_window_sec is None:
            return RuntimeCheckResult(True)

        ts = now if now is not None else time.monotonic()
        count = self._count_in_window(
            self._creation_ts, user_id, ts, rules.creation_window_sec,
        )
        if count >= rules.creations_per_window:
            return RuntimeCheckResult(
                False,
                reason="macro_rate_limit_exceeded",
                rule_source="macro_bot_defense",
            )
        return RuntimeCheckResult(True)

    def check_destroy_allowed(
        self,
        user_id: str,
        *,
        now: float | None = None,
    ) -> RuntimeCheckResult:
        rules = self.merged_rules()
        if rules.max_destroys_per_window is None or rules.destroy_window_sec is None:
            return RuntimeCheckResult(True)

        ts = now if now is not None else time.monotonic()
        count = self._count_in_window(
            self._destroy_ts, user_id, ts, rules.destroy_window_sec,
        )
        if count >= rules.max_destroys_per_window:
            return RuntimeCheckResult(
                False,
                reason="creative_destruction_limit_exceeded",
                rule_source="creative_destruction",
            )
        return RuntimeCheckResult(True)

    def check_npc_creation_allowed(
        self,
        npc_id: str,
        *,
        now: float | None = None,
    ) -> RuntimeCheckResult:
        rules = self.merged_rules()
        if rules.block_npc_creation:
            return RuntimeCheckResult(
                False,
                reason="npc_creation_blocked_by_system",
                rule_source="macro_bot_defense",
            )
        if rules.npc_creations_per_window is None or rules.npc_window_sec is None:
            return RuntimeCheckResult(True)

        ts = now if now is not None else time.monotonic()
        count = self._count_in_window(
            self._npc_creation_ts, npc_id, ts, rules.npc_window_sec,
        )
        if count >= rules.npc_creations_per_window:
            return RuntimeCheckResult(
                False,
                reason="npc_rate_limit_exceeded",
                rule_source="macro_bot_defense",
            )
        return RuntimeCheckResult(True)

    def penalty_multiplier(self) -> float:
        return self.merged_rules().destroy_penalty_multiplier

    def cross_destroy_scale(self) -> float:
        return max(1.0, self.merged_rules().cross_destroy_scale)

    def record_creation(self, user_id: str, *, now: float | None = None) -> None:
        self._append_ts(self._creation_ts, user_id, now)

    def record_destroy(self, user_id: str, *, now: float | None = None) -> None:
        self._append_ts(self._destroy_ts, user_id, now)

    def record_npc_creation(self, npc_id: str, *, now: float | None = None) -> None:
        self._append_ts(self._npc_creation_ts, npc_id, now)

    def _merge_spec(self, rules: RuntimeRules, system: EnactedSystem) -> None:
        spec = system.spec
        kind = system.kind

        if kind == SystemProposalKind.MACRO_BOT_DEFENSE:
            if "min_creator_cooldown_sec" in spec:
                val = float(spec["min_creator_cooldown_sec"])
                rules.min_creator_cooldown_sec = max(
                    rules.min_creator_cooldown_sec or 0.0, val,
                )
            if "max_creations_per_creator_per_pulse" in spec:
                val = int(spec["max_creations_per_creator_per_pulse"])
                cur = rules.max_creations_per_creator_per_pulse
                rules.max_creations_per_creator_per_pulse = (
                    min(cur, val) if cur is not None else val
                )
            if "creations_per_window" in spec:
                val = int(spec["creations_per_window"])
                cur = rules.creations_per_window
                rules.creations_per_window = min(cur, val) if cur is not None else val
            if "window_sec" in spec:
                rules.creation_window_sec = float(spec["window_sec"])
            if spec.get("block_npc_creation"):
                rules.block_npc_creation = True
            if "npc_creations_per_window" in spec:
                val = int(spec["npc_creations_per_window"])
                cur = rules.npc_creations_per_window
                rules.npc_creations_per_window = (
                    min(cur, val) if cur is not None else val
                )
            if "npc_window_sec" in spec:
                rules.npc_window_sec = float(spec["npc_window_sec"])

        elif kind == SystemProposalKind.CREATIVE_DESTRUCTION:
            if "max_destroys_per_window" in spec:
                val = int(spec["max_destroys_per_window"])
                cur = rules.max_destroys_per_window
                rules.max_destroys_per_window = (
                    min(cur, val) if cur is not None else val
                )
            if "destroy_window_sec" in spec:
                rules.destroy_window_sec = float(spec["destroy_window_sec"])
            if "penalty_multiplier" in spec:
                mult = float(spec["penalty_multiplier"])
                rules.destroy_penalty_multiplier = min(
                    rules.destroy_penalty_multiplier, mult,
                )

        elif kind == SystemProposalKind.ELECTION_WAR:
            if "cross_destroy_scale" in spec:
                rules.cross_destroy_scale = max(
                    rules.cross_destroy_scale,
                    float(spec["cross_destroy_scale"]),
                )

        elif kind == SystemProposalKind.CUSTOM:
            if "governance_approval_ratio" in spec:
                val = float(spec["governance_approval_ratio"])
                cur = rules.governance_approval_ratio
                rules.governance_approval_ratio = (
                    max(cur, val) if cur is not None else val
                )
            if "creations_per_window" in spec:
                val = int(spec["creations_per_window"])
                cur = rules.creations_per_window
                rules.creations_per_window = (
                    min(cur, val) if cur is not None else val
                )
            if "window_sec" in spec:
                rules.creation_window_sec = float(spec["window_sec"])

    def _append_ts(
        self,
        store: dict[str, list[float]],
        key: str,
        now: float | None,
    ) -> None:
        ts = now if now is not None else time.monotonic()
        store.setdefault(key, []).append(ts)

    def _count_in_window(
        self,
        store: dict[str, list[float]],
        key: str,
        now: float,
        window_sec: float,
    ) -> int:
        entries = store.get(key, [])
        cutoff = now - window_sec
        entries = [t for t in entries if t >= cutoff]
        store[key] = entries
        return len(entries)
