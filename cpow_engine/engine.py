"""CPoW Simulation orchestrator — 틱 루프 + 3대 모듈 통합."""

from __future__ import annotations

from cpow_engine.cpow import CPoWEngine, CPoWScore
from cpow_engine.models import (
    ActionRecord,
    CreativeObject,
    InteractionResult,
    SimulationState,
    WorldDelta,
)
from cpow_engine.physics import DefinitionPhysicsEngine
from cpow_engine.physics.crossover import CrossoverPhysics
from cpow_engine.physics.equilibrium import EquilibriumRegulator, EquilibriumReport
from cpow_engine.physics.extended_physics import ExtendedPhysicsEngine
from cpow_engine.physics.fields import FieldPhysics
from cpow_engine.physics.phase import PhaseChangePhysics
from cpow_engine.shared_state import SharedStateSync, StatePatch


class SimulationEngine:
    """자율 시뮬레이션 엔진 — 매 틱마다 상태가 동적으로 변화."""

    def __init__(self, seed_state: SimulationState | None = None) -> None:
        self.state = seed_state or SimulationState()
        self.physics = DefinitionPhysicsEngine()
        self.extended = ExtendedPhysicsEngine()
        self.fields = FieldPhysics()
        self.crossover = CrossoverPhysics()
        self.phase = PhaseChangePhysics()
        self.equilibrium = EquilibriumRegulator()
        self.cpow = CPoWEngine()
        self.sync = SharedStateSync()
        self.last_equilibrium: EquilibriumReport | None = None

    def create_object(self, obj: CreativeObject) -> ActionRecord:
        """유저 창조 행위 — 오브젝트 등록."""
        self.state.objects[obj.id] = obj
        action = ActionRecord(
            actor_id=obj.creator_id,
            action_type="create_object",
            payload={"object_id": obj.id, "label": obj.label},
        )
        self.state.action_log.append(action)
        return action

    def connect_objects(self, source_id: str, target_id: str) -> ActionRecord:
        """오브젝트 연결 — 상호작용 경로 생성."""
        source = self.state.objects[source_id]
        if target_id not in source.connections:
            source.connections.append(target_id)
        action = ActionRecord(
            actor_id=source.creator_id,
            action_type="connect",
            payload={"source_id": source_id, "target_id": target_id},
        )
        self.state.action_log.append(action)
        return action

    def tick(self) -> tuple[WorldDelta, CPoWScore | None]:
        """한 틱 진행: 기본·확장·환경장 → 교차 → 피드백 → 상변화 → 균형."""
        self.state.tick += 1

        base_interactions = self.physics.resolve_interactions(self.state.objects)
        extended_interactions = self.extended.resolve(self.state.objects)
        field_interactions = self.fields.resolve(
            self.state.objects,
            energy_pool=self.state.energy_pool,
        )
        cross_interactions = self.crossover.resolve(
            self.state.objects,
            energy_pool=self.state.energy_pool,
        )
        interactions = (
            base_interactions
            + extended_interactions
            + field_interactions
            + cross_interactions
        )

        self.extended.apply_feedback(self.state.objects, interactions)
        self.fields.apply_feedback(self.state.objects, interactions)
        self.crossover.apply_feedback(self.state.objects, interactions)

        phase_events = self.phase.apply(self.state.objects, interactions)
        interactions = interactions + phase_events

        energy_from_physics = sum(i.energy_delta for i in interactions)
        self.state.energy_pool += energy_from_physics

        eq_report = self.equilibrium.regulate(self.state, interactions)
        self.last_equilibrium = eq_report

        delta = WorldDelta(
            tick=self.state.tick,
            interactions=interactions,
            state_changes={
                "energy_pool": self.state.energy_pool,
                "balance_index": eq_report.balance_index,
                "crossover_count": len(cross_interactions),
                "extended_count": len(extended_interactions),
                "field_count": len(field_interactions),
                "phase_count": len(phase_events),
                "interaction_count": len(interactions),
            },
        )

        score: CPoWScore | None = None
        if self.state.action_log:
            last_action = self.state.action_log[-1]
            score = self.cpow.score_action(last_action, delta, self.state)

        self.state.entropy = self._local_entropy()
        self.state.version += 1
        return delta, score

    def apply_remote_patches(self, patches: list[StatePatch]) -> SimulationState:
        """다중 유저 패치 병합."""
        result = self.sync.apply_patches(self.state, patches)
        self.state = result.state
        return self.state

    def _local_entropy(self) -> float:
        if not self.state.objects:
            return 0.0
        fps = {o.creativity_fingerprint for o in self.state.objects.values()}
        return len(fps) / len(self.state.objects)
