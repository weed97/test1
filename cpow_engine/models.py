"""Core data schemas — 데이터 구조가 곧 법."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class PropertyDef:
    """유저가 정의한 물리 속성 (하드코딩된 Fire가 아님)."""

    name: str
    value: float
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value, "unit": self.unit}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PropertyDef:
        return cls(
            name=str(data["name"]),
            value=float(data["value"]),
            unit=str(data.get("unit", "")),
        )


@dataclass
class CreativeObject:
    """유저가 창조한 오브젝트 — 속성 집합으로만 정의."""

    id: str = field(default_factory=_new_id)
    creator_id: str = ""
    label: str = ""
    properties: list[PropertyDef] = field(default_factory=list)
    connections: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    creativity_fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.creativity_fingerprint:
            self.creativity_fingerprint = self._compute_fingerprint()

    def get_property(self, name: str) -> PropertyDef | None:
        for prop in self.properties:
            if prop.name.lower() == name.lower():
                return prop
        return None

    def _compute_fingerprint(self) -> str:
        payload = {
            "label": self.label,
            "properties": sorted(
                [(p.name, p.value, p.unit) for p in self.properties]
            ),
            "connections": sorted(self.connections),
        }
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "label": self.label,
            "properties": [p.to_dict() for p in self.properties],
            "connections": list(self.connections),
            "created_at": self.created_at,
            "creativity_fingerprint": self.creativity_fingerprint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CreativeObject:
        obj = cls(
            id=str(data.get("id", _new_id())),
            creator_id=str(data.get("creator_id", "")),
            label=str(data.get("label", "")),
            properties=[
                PropertyDef.from_dict(p) for p in data.get("properties", [])
            ],
            connections=list(data.get("connections", [])),
            created_at=float(data.get("created_at", time.time())),
            creativity_fingerprint=str(data.get("creativity_fingerprint", "")),
        )
        return obj


@dataclass
class InteractionResult:
    """속성 조합으로 계산된 물리적 결과."""

    source_id: str
    target_id: str | None
    effect_type: str
    magnitude: float
    energy_delta: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "effect_type": self.effect_type,
            "magnitude": self.magnitude,
            "energy_delta": self.energy_delta,
            "metadata": dict(self.metadata),
        }


@dataclass
class ActionRecord:
    """유저 행동 데이터 — CPoW 입력."""

    actor_id: str
    action_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "action_type": self.action_type,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


@dataclass
class WorldDelta:
    """환경 변화 스냅샷."""

    tick: int
    objects_added: list[str] = field(default_factory=list)
    objects_removed: list[str] = field(default_factory=list)
    interactions: list[InteractionResult] = field(default_factory=list)
    state_changes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "objects_added": list(self.objects_added),
            "objects_removed": list(self.objects_removed),
            "interactions": [i.to_dict() for i in self.interactions],
            "state_changes": dict(self.state_changes),
        }


@dataclass
class SimulationState:
    """동적 시뮬레이션 상태 — 매 틱마다 변화."""

    tick: int = 0
    objects: dict[str, CreativeObject] = field(default_factory=dict)
    energy_pool: float = 0.0
    entropy: float = 0.0
    action_log: list[ActionRecord] = field(default_factory=list)
    version: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "objects": {k: v.to_dict() for k, v in self.objects.items()},
            "energy_pool": self.energy_pool,
            "entropy": self.entropy,
            "action_log": [a.to_dict() for a in self.action_log[-100:]],
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationState:
        return cls(
            tick=int(data.get("tick", 0)),
            objects={
                k: CreativeObject.from_dict(v)
                for k, v in data.get("objects", {}).items()
            },
            energy_pool=float(data.get("energy_pool", 0.0)),
            entropy=float(data.get("entropy", 0.0)),
            version=int(data.get("version", 0)),
        )
