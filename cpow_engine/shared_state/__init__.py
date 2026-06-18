"""Shared State — 충돌 시 Merge/Negotiation 프로토콜."""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cpow_engine.models import CreativeObject, SimulationState


class ConflictStrategy(Enum):
    MERGE = "merge"
    NEGOTIATE = "negotiate"
    LAST_WRITE_WINS = "last_write_wins"
    REJECT = "reject"


@dataclass
class StatePatch:
    """유저가 제출한 상태 변경 조각."""

    author_id: str
    base_version: int
    objects: dict[str, CreativeObject] = field(default_factory=dict)
    energy_delta: float = 0.0
    timestamp: float = field(default_factory=time.time)
    patch_id: str = ""

    def __post_init__(self) -> None:
        if not self.patch_id:
            self.patch_id = f"{self.author_id}:{int(self.timestamp * 1000)}"


@dataclass
class ConflictRecord:
    """충돌 기록 — 오류가 아닌 병합 대상."""

    patch_a: StatePatch
    patch_b: StatePatch
    conflicting_keys: list[str]
    resolution: str = ""
    merged_objects: dict[str, CreativeObject] = field(default_factory=dict)


@dataclass
class MergeResult:
    state: SimulationState
    conflicts_resolved: list[ConflictRecord]
    strategy_used: ConflictStrategy


class SharedStateSync:
    """다중 유저 물리 정의 충돌 → Merge/Negotiation."""

    def __init__(
        self,
        default_strategy: ConflictStrategy = ConflictStrategy.MERGE,
    ) -> None:
        self.default_strategy = default_strategy
        self._negotiation_queue: list[ConflictRecord] = []

    def apply_patches(
        self,
        base: SimulationState,
        patches: list[StatePatch],
        *,
        strategy: ConflictStrategy | None = None,
    ) -> MergeResult:
        strategy = strategy or self.default_strategy
        state = copy.deepcopy(base)
        conflicts: list[ConflictRecord] = []

        remaining = sorted(patches, key=lambda p: p.timestamp)

        while remaining:
            batch = [p for p in remaining if p.base_version == state.version]
            if not batch:
                break
            remaining = [p for p in remaining if p.base_version != state.version]

            key_patches: dict[str, list[CreativeObject]] = {}
            for patch in batch:
                for key, obj in patch.objects.items():
                    key_patches.setdefault(key, []).append(obj)

            for key, objs in key_patches.items():
                if key in state.objects and len(objs) == 1:
                    existing = state.objects[key]
                    incoming = objs[0]
                    if existing.creativity_fingerprint != incoming.creativity_fingerprint:
                        conflict = ConflictRecord(
                            patch_a=StatePatch("incoming", state.version, {key: incoming}),
                            patch_b=StatePatch("base", state.version, {key: existing}),
                            conflicting_keys=[key],
                        )
                        resolved = self._resolve(conflict, strategy)
                        conflicts.append(resolved)
                        state.objects.update(resolved.merged_objects)
                        continue

                if len(objs) > 1:
                    merged = objs[0]
                    for other in objs[1:]:
                        merged = self._merge_objects(merged, other)
                    conflict = ConflictRecord(
                        patch_a=StatePatch(batch[0].author_id, state.version, {key: objs[0]}),
                        patch_b=StatePatch(batch[-1].author_id, state.version, {key: objs[-1]}),
                        conflicting_keys=[key],
                        resolution="concurrent_merge",
                        merged_objects={key: merged},
                    )
                    conflicts.append(conflict)
                    state.objects[key] = merged
                else:
                    state.objects[key] = objs[0]

            for patch in batch:
                state.energy_pool += patch.energy_delta

            state.version += 1

        state.entropy = self._compute_entropy(state)
        return MergeResult(
            state=state,
            conflicts_resolved=conflicts,
            strategy_used=strategy,
        )

    def negotiate(
        self, conflict: ConflictRecord
    ) -> dict[str, CreativeObject]:
        """중재: 속성 값의 가중 평균 + 연결 합집합."""
        merged: dict[str, CreativeObject] = {}
        for key in conflict.conflicting_keys:
            obj_a = conflict.patch_a.objects.get(key)
            obj_b = conflict.patch_b.objects.get(key)
            if obj_a and obj_b:
                merged[key] = self._merge_objects(obj_a, obj_b)
            elif obj_a:
                merged[key] = obj_a
            elif obj_b:
                merged[key] = obj_b
        conflict.resolution = "negotiated_weighted_average"
        conflict.merged_objects = merged
        return merged

    def _detect_conflict(
        self,
        patch: StatePatch,
        state: SimulationState,
        overlapping: set[str],
    ) -> ConflictRecord:
        conflicting: list[str] = []
        for key in overlapping:
            existing = state.objects[key]
            incoming = patch.objects[key]
            if existing.creativity_fingerprint != incoming.creativity_fingerprint:
                conflicting.append(key)

        dummy_b = StatePatch(
            author_id="system",
            base_version=state.version,
            objects={k: state.objects[k] for k in conflicting},
        )
        return ConflictRecord(
            patch_a=patch,
            patch_b=dummy_b,
            conflicting_keys=conflicting,
        )

    def _resolve(
        self,
        conflict: ConflictRecord,
        strategy: ConflictStrategy,
    ) -> ConflictRecord:
        if strategy == ConflictStrategy.MERGE:
            merged = self.negotiate(conflict)
            conflict.resolution = "merged"
            conflict.merged_objects = merged
        elif strategy == ConflictStrategy.NEGOTIATE:
            merged = self.negotiate(conflict)
            self._negotiation_queue.append(conflict)
            conflict.resolution = "negotiated"
            conflict.merged_objects = merged
        elif strategy == ConflictStrategy.LAST_WRITE_WINS:
            conflict.merged_objects = dict(conflict.patch_a.objects)
            conflict.resolution = "last_write_wins"
        else:
            conflict.resolution = "rejected"
            conflict.merged_objects = {}

        return conflict

    def _merge_objects(
        self, a: CreativeObject, b: CreativeObject
    ) -> CreativeObject:
        """두 창조물의 속성을 가중 평균으로 병합."""
        prop_map: dict[str, list[float]] = {}
        unit_map: dict[str, str] = {}

        for obj in (a, b):
            for prop in obj.properties:
                prop_map.setdefault(prop.name, []).append(prop.value)
                unit_map[prop.name] = prop.unit

        from cpow_engine.models import PropertyDef

        merged_props = [
            PropertyDef(
                name=name,
                value=sum(vals) / len(vals),
                unit=unit_map.get(name, ""),
            )
            for name, vals in prop_map.items()
        ]

        connections = list(set(a.connections) | set(b.connections))
        creators = {a.creator_id, b.creator_id} - {""}

        return CreativeObject(
            id=a.id,
            creator_id="|".join(sorted(creators)),
            label=a.label or b.label,
            properties=merged_props,
            connections=connections,
        )

    def _compute_entropy(self, state: SimulationState) -> float:
        if not state.objects:
            return 0.0
        fps = {o.creativity_fingerprint for o in state.objects.values()}
        return len(fps) / len(state.objects)

    @property
    def pending_negotiations(self) -> list[ConflictRecord]:
        return list(self._negotiation_queue)

    def clear_negotiations(self) -> None:
        self._negotiation_queue.clear()
