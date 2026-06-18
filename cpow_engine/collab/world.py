"""협동 오픈월드 — 공유 상태 + 감쇄 병합 + 빌드 펄스."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from cpow_engine.collab.noise_gate import ChangeVerdict, NoiseGate
from cpow_engine.collab.policy import CollabPolicy, load_collab_policy
from cpow_engine.collab.pulse import AppliedCreationResult, PendingCreation, PulseResult
from cpow_engine.engine import SimulationEngine
from cpow_engine.models import CreativeObject, SimulationState, WorldDelta
from cpow_engine.cpow import CPoWScore
from cpow_engine.shared_state import SharedStateSync, StatePatch


@dataclass
class WorldSubmissionResult:
    ok: bool
    object_id: str = ""
    verdict: ChangeVerdict | None = None
    tick: int = 0
    world_version: int = 0
    contributors_this_tick: int = 0
    reason: str = ""
    queued: bool = False
    pulse_number: int = 0
    pending_count: int = 0
    contributors_in_pulse: int = 0
    seconds_until_pulse: float = 0.0
    cooldown_remaining: float = 0.0
    proposal_id: str = ""
    law_violations: list[str] = field(default_factory=list)
    consensus_pending: bool = False
    approvals_needed: int = 0
    approvals_received: int = 0
    penalty_redeemed: float = 0.0


@dataclass
class ContributorStats:
    creator_id: str
    submissions: int = 0
    accepted: int = 0
    damped: int = 0
    rejected: int = 0
    queued: int = 0


class CollaborativeWorld:
    """다인이 함께 창조하는 오픈월드 — 펄스마다 모아 반영, 큰 변화는 감쇄."""

    def __init__(
        self,
        world_id: str,
        policy: CollabPolicy | None = None,
        *,
        now: float | None = None,
    ) -> None:
        self.world_id = world_id
        self.policy = policy or load_collab_policy()
        self.engine = SimulationEngine()
        self.sync = SharedStateSync()
        self.gate = NoiseGate(self.policy)
        self._recent_verdicts: list[ChangeVerdict] = []
        self._contributors: dict[str, ContributorStats] = {}
        self._pending: list[PendingCreation] = []
        self._pulse_number: int = 0
        self._pulse_anchor_at: float | None = None
        self._last_pulse_at: float = now if now is not None else time.monotonic()
        self._creator_last_queue_at: dict[str, float] = {}
        self._now_override: float | None = now

    def _clock(self) -> float:
        return self._now_override if self._now_override is not None else time.monotonic()

    def set_time(self, now: float) -> None:
        """테스트용 — 가상 시각 주입."""
        self._now_override = now

    @property
    def state(self) -> SimulationState:
        return self.engine.state

    def submit_creation(
        self,
        creator_id: str,
        obj: CreativeObject,
        *,
        creativity_score: float = 1.0,
    ) -> WorldSubmissionResult:
        """창조를 큐에 넣음 — 펄스 시점에 함께 반영."""
        now = self._clock()
        stats = self._stats_for(creator_id)
        stats.submissions += 1

        cooldown_left = self._cooldown_remaining(creator_id, now)
        if cooldown_left > 0:
            stats.rejected += 1
            return self._queue_response(
                False,
                reason="creator_cooldown",
                cooldown_remaining=cooldown_left,
            )

        if self._creator_pending_count(creator_id) >= (
            self.policy.max_creations_per_creator_per_pulse
        ):
            stats.rejected += 1
            return self._queue_response(
                False,
                reason="creator_pulse_limit_reached",
            )

        if len(self._pending) >= self.policy.max_creations_per_tick:
            stats.rejected += 1
            return self._queue_response(
                False,
                reason="pulse_queue_full",
            )

        if not self._pending and self.policy.pulse_interval_sec > 0:
            self._pulse_anchor_at = now

        self._pending.append(
            PendingCreation(creator_id, obj, creativity_score, now)
        )
        self._creator_last_queue_at[creator_id] = now
        stats.queued += 1

        result = self._queue_response(
            True,
            object_id=obj.id,
            reason="queued_for_pulse",
            queued=True,
        )

        if self.policy.pulse_interval_sec <= 0:
            pulse = self.advance_pulse(force=True, now=now)
            if pulse.advanced and pulse.results:
                applied = pulse.results[-1]
                return WorldSubmissionResult(
                    ok=applied.ok,
                    object_id=applied.object_id,
                    verdict=applied.verdict,
                    tick=self.state.tick,
                    world_version=self.state.version,
                    reason=applied.reason,
                    queued=False,
                    pulse_number=pulse.pulse_number,
                )

        return result

    def advance_pulse(
        self,
        *,
        force: bool = False,
        now: float | None = None,
    ) -> PulseResult:
        """대기 중인 창조를 한꺼번에 반영하고 시뮬레이션 틱을 진행."""
        ts = self._clock() if now is None else now
        interval = self.policy.pulse_interval_sec

        if not force and interval > 0:
            elapsed = ts - self._pulse_anchor_at if self._pulse_anchor_at is not None else 0.0
            if not self._pending or elapsed < interval:
                return PulseResult(
                    advanced=False,
                    pulse_number=self._pulse_number,
                    reason="pulse_not_ready",
                    seconds_until_next=self.seconds_until_pulse(ts),
                )

        if not self._pending:
            return PulseResult(
                advanced=False,
                pulse_number=self._pulse_number,
                reason="pulse_queue_empty",
            )

        applied: list[AppliedCreationResult] = []
        for pending in list(self._pending):
            applied.append(self._apply_pending(pending))

        self._pending.clear()
        self._pulse_number += 1
        self._last_pulse_at = ts
        self._pulse_anchor_at = None

        delta, score = self.engine.tick()

        return PulseResult(
            advanced=True,
            pulse_number=self._pulse_number,
            applied_count=sum(1 for r in applied if r.ok),
            results=applied,
            delta=delta,
            score=score,
            reason="pulse_committed",
            seconds_until_next=interval if interval > 0 else 0.0,
        )

    def maybe_advance_pulse(self, now: float | None = None) -> PulseResult:
        """펄스 간격이 지났으면 자동 반영."""
        return self.advance_pulse(force=False, now=now)

    def seconds_until_pulse(self, now: float | None = None) -> float:
        if self.policy.pulse_interval_sec <= 0:
            return 0.0
        if not self._pending:
            return 0.0
        ts = self._clock() if now is None else now
        anchor = self._pulse_anchor_at if self._pulse_anchor_at is not None else ts
        return max(0.0, self.policy.pulse_interval_sec - (ts - anchor))

    def pending_preview(self) -> list[dict[str, str]]:
        return [
            {
                "creator_id": p.creator_id,
                "label": p.obj.label,
                "object_id": p.obj.id,
            }
            for p in self._pending
        ]

    def submit_patches(self, patches: list[StatePatch]) -> WorldSubmissionResult:
        """다중 유저 패치 — 감쇄 후 병합."""
        if len(patches) > self.policy.max_patches_per_batch:
            patches = patches[: self.policy.max_patches_per_batch]

        damped_patches: list[StatePatch] = []
        for patch in patches:
            damped_objects: dict[str, CreativeObject] = {}
            for oid, incoming in patch.objects.items():
                if oid in self.state.objects:
                    v = self.gate.evaluate_update(
                        self.state.objects[oid], incoming,
                    )
                    if v.accepted and v.object:
                        damped_objects[oid] = v.object
                else:
                    v = self.gate.evaluate_new(incoming, self.state)
                    if v.accepted and v.object:
                        damped_objects[oid] = v.object
            if damped_objects:
                damped_patches.append(StatePatch(
                    patch.author_id,
                    patch.base_version,
                    damped_objects,
                    patch.energy_delta * self.policy.damp_factor,
                ))

        if not damped_patches:
            return WorldSubmissionResult(False, reason="all_patches_filtered")

        self.engine.apply_remote_patches(damped_patches)
        return WorldSubmissionResult(
            True,
            tick=self.state.tick,
            world_version=self.state.version,
            reason="patches_merged_damped",
        )

    def advance_tick(self) -> tuple[WorldDelta, CPoWScore | None]:
        """레거시 틱 진행 — 펄스 없이 물리만 한 스텝."""
        return self.engine.tick()

    def world_noise_level(self) -> float:
        if not self._recent_verdicts:
            return 0.0
        return sum(v.magnitude for v in self._recent_verdicts[-20:]) / min(
            20, len(self._recent_verdicts)
        )

    def contributor_stats(self) -> dict[str, dict[str, int]]:
        return {
            k: {
                "submissions": v.submissions,
                "accepted": v.accepted,
                "damped": v.damped,
                "rejected": v.rejected,
                "queued": v.queued,
            }
            for k, v in self._contributors.items()
        }

    def to_public_dict(self) -> dict:
        return {
            "world_id": self.world_id,
            "tick": self.state.tick,
            "version": self.state.version,
            "object_count": len(self.state.objects),
            "energy_pool": self.state.energy_pool,
            "entropy": self.state.entropy,
            "noise_level": round(self.world_noise_level(), 4),
            "pulse_number": self._pulse_number,
            "pending_count": len(self._pending),
            "contributors_in_pulse": len({p.creator_id for p in self._pending}),
            "seconds_until_pulse": round(self.seconds_until_pulse(), 2),
            "pending": self.pending_preview(),
            "policy": self.policy.to_dict(),
            "contributors": self.contributor_stats(),
            "physics_balance": (
                self.engine.last_equilibrium.to_dict()
                if self.engine.last_equilibrium is not None
                else {}
            ),
        }

    def _apply_pending(self, pending: PendingCreation) -> AppliedCreationResult:
        stats = self._stats_for(pending.creator_id)
        obj = pending.obj

        if obj.id in self.state.objects:
            verdict = self.gate.evaluate_update(
                self.state.objects[obj.id],
                obj,
                creativity_score=pending.creativity_score,
            )
        else:
            verdict = self.gate.evaluate_new(obj, self.state)

        self._recent_verdicts.append(verdict)
        if len(self._recent_verdicts) > 100:
            self._recent_verdicts.pop(0)

        if not verdict.accepted or verdict.object is None:
            stats.rejected += 1
            return AppliedCreationResult(
                False,
                pending.creator_id,
                object_id=obj.id,
                verdict=verdict,
                reason=verdict.reason,
            )

        accepted_obj = verdict.object
        accepted_obj.creator_id = pending.creator_id

        if obj.id in self.state.objects:
            self.state.objects[accepted_obj.id] = accepted_obj
        else:
            self.engine.create_object(accepted_obj)

        if verdict.magnitude > self.policy.noise_threshold:
            stats.damped += 1
        else:
            stats.accepted += 1

        return AppliedCreationResult(
            True,
            pending.creator_id,
            object_id=accepted_obj.id,
            verdict=verdict,
            reason=verdict.reason,
        )

    def _cooldown_remaining(self, creator_id: str, now: float) -> float:
        cooldown = self.policy.min_creator_cooldown_sec
        if cooldown <= 0:
            return 0.0
        last = self._creator_last_queue_at.get(creator_id)
        if last is None:
            return 0.0
        return max(0.0, cooldown - (now - last))

    def _creator_pending_count(self, creator_id: str) -> int:
        return sum(1 for p in self._pending if p.creator_id == creator_id)

    def _queue_response(
        self,
        ok: bool,
        *,
        object_id: str = "",
        reason: str = "",
        queued: bool = False,
        cooldown_remaining: float = 0.0,
    ) -> WorldSubmissionResult:
        now = self._clock()
        return WorldSubmissionResult(
            ok=ok,
            object_id=object_id,
            tick=self.state.tick,
            world_version=self.state.version,
            reason=reason,
            queued=queued,
            pulse_number=self._pulse_number + (1 if queued else 0),
            pending_count=len(self._pending),
            contributors_in_pulse=len({p.creator_id for p in self._pending}),
            seconds_until_pulse=self.seconds_until_pulse(now),
            cooldown_remaining=cooldown_remaining,
        )

    def _stats_for(self, creator_id: str) -> ContributorStats:
        if creator_id not in self._contributors:
            self._contributors[creator_id] = ContributorStats(creator_id=creator_id)
        return self._contributors[creator_id]
