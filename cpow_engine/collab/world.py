"""협동 오픈월드 — 공유 상태 + 감쇄 병합."""

from __future__ import annotations

import time
from dataclasses import dataclass

from cpow_engine.collab.noise_gate import ChangeVerdict, NoiseGate
from cpow_engine.collab.policy import CollabPolicy, load_collab_policy
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


@dataclass
class ContributorStats:
    creator_id: str
    submissions: int = 0
    accepted: int = 0
    damped: int = 0
    rejected: int = 0


class CollaborativeWorld:
    """다인이 함께 창조하는 오픈월드 — 큰 변화는 자동 감쇄."""

    def __init__(
        self,
        world_id: str,
        policy: CollabPolicy | None = None,
    ) -> None:
        self.world_id = world_id
        self.policy = policy or load_collab_policy()
        self.engine = SimulationEngine()
        self.sync = SharedStateSync()
        self.gate = NoiseGate(self.policy)
        self._creations_this_pulse: int = 0
        self._recent_verdicts: list[ChangeVerdict] = []
        self._contributors: dict[str, ContributorStats] = {}

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
        if self._creations_this_pulse >= self.policy.max_creations_per_tick:
            return WorldSubmissionResult(
                False, reason="pulse_creation_cap_reached",
                tick=self.state.tick,
                world_version=self.state.version,
            )

        stats = self._stats_for(creator_id)
        stats.submissions += 1

        if obj.id in self.state.objects:
            verdict = self.gate.evaluate_update(
                self.state.objects[obj.id], obj, creativity_score=creativity_score,
            )
        else:
            verdict = self.gate.evaluate_new(obj, self.state)

        self._recent_verdicts.append(verdict)
        if len(self._recent_verdicts) > 100:
            self._recent_verdicts.pop(0)

        if not verdict.accepted or verdict.object is None:
            stats.rejected += 1
            return WorldSubmissionResult(
                False,
                verdict=verdict,
                tick=self.state.tick,
                world_version=self.state.version,
                reason=verdict.reason,
            )

        accepted_obj = verdict.object
        accepted_obj.creator_id = creator_id

        if obj.id in self.state.objects:
            self.state.objects[accepted_obj.id] = accepted_obj
        else:
            self.engine.create_object(accepted_obj)

        self._creations_this_pulse += 1

        if verdict.magnitude > self.policy.noise_threshold:
            stats.damped += 1
        else:
            stats.accepted += 1

        return WorldSubmissionResult(
            True,
            object_id=accepted_obj.id,
            verdict=verdict,
            tick=self.state.tick,
            world_version=self.state.version,
            contributors_this_tick=self._creations_this_pulse,
            reason=verdict.reason,
        )

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
        """월드 틱 진행 — 한 펄스 창조 상한 리셋."""
        self._creations_this_pulse = 0
        return self.engine.tick()

    def world_noise_level(self) -> float:
        """월드 노이즈 지표 — 최근 변화량 평균."""
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
            "policy": self.policy.to_dict(),
            "contributors": self.contributor_stats(),
        }

    def _stats_for(self, creator_id: str) -> ContributorStats:
        if creator_id not in self._contributors:
            self._contributors[creator_id] = ContributorStats(creator_id=creator_id)
        return self._contributors[creator_id]
