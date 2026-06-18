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
from cpow_engine.shared_state import SharedStateSync, StatePatch


class SimulationEngine:
    """자율 시뮬레이션 엔진 — 매 틱마다 상태가 동적으로 변화."""

    def __init__(self, seed_state: SimulationState | None = None) -> None:
        self.state = seed_state or SimulationState()
        self.physics = DefinitionPhysicsEngine()
        self.crossover = CrossoverPhysics()
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
        """한 틱 진행: 물리 상호작용 → 교차 결합 → 피드백 → 균형 조절."""
        self.state.tick += 1

        base_interactions = self.physics.resolve_interactions(self.state.objects)
        cross_interactions = self.crossover.resolve(
            self.state.objects,
            energy_pool=self.state.energy_pool,
        )
        interactions = base_interactions + cross_interactions
        self.crossover.apply_feedback(self.state.objects, interactions)

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
