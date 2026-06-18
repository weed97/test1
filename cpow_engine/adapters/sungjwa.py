"""성좌 헌터 sungjwa_hunter_sim event → CPoW ActionRecord + CreativeObject."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cpow_engine.adapters.fantasy import AdapterResult
from cpow_engine.models import ActionRecord, CreativeObject, PropertyDef
from cpow_engine.physics import create_heat_object, create_material_object
from cpow_engine.schema import SchemaValidator

_COMBAT_KINDS = frozenset({"combat", "gate", "battle"})


@dataclass
class SungjwaEventAdapter:
    """Map hunter sim EventRecord dicts to CPoW data."""

    validator: SchemaValidator | None = None

    def __post_init__(self) -> None:
        if self.validator is None:
            self.validator = SchemaValidator()

    def from_event(
        self,
        actor_id: str,
        event: dict[str, Any],
    ) -> AdapterResult:
        kind = str(event.get("kind", "misc")).lower()
        title = str(event.get("title", kind))
        effects: dict[str, Any] = event.get("effects", {})
        turn = int(event.get("turn", 0))

        if kind in _COMBAT_KINDS or "전투" in title or "게이트" in str(
            event.get("description", "")
        ):
            return self._combat_result(actor_id, event, effects, turn)

        favor_delta = int(effects.get("favor", 0))
        if favor_delta != 0:
            return self._constellation_pulse(actor_id, title, favor_delta, turn)

        heat = max(15.0, float(abs(effects.get("exp", 10))) * 0.5)
        obj = create_heat_object(actor_id, f"hunter_{kind}", heat)
        return self._pack(actor_id, obj, kind, turn, event)

    def from_game_state(self, actor_id: str, state: dict[str, Any]) -> list[AdapterResult]:
        """Convert recent event log entries."""
        log = state.get("log", [])
        results: list[AdapterResult] = []
        for entry in log[-10:]:
            if isinstance(entry, dict):
                results.append(self.from_event(actor_id, entry))
        return results

    def _combat_result(
        self,
        actor_id: str,
        event: dict[str, Any],
        effects: dict[str, Any],
        turn: int,
    ) -> AdapterResult:
        exp = max(0, int(effects.get("exp", 0)))
        hp_loss = abs(int(effects.get("hp", 0)))
        intensity = 40.0 + exp * 0.4 + hp_loss * 0.2
        obj = create_heat_object(actor_id, "gate_clash", intensity)
        obj.properties.append(
            PropertyDef("combat_entropy", min(1.0, exp / 100.0), "ratio")
        )
        return self._pack(actor_id, obj, "combat", turn, event)

    def _constellation_pulse(
        self,
        actor_id: str,
        title: str,
        favor_delta: int,
        turn: int,
    ) -> AdapterResult:
        material = "constellation_favor" if favor_delta > 0 else "constellation_doubt"
        obj = create_material_object(actor_id, title[:24], material)
        obj.properties.append(
            PropertyDef("favor_delta", float(favor_delta), "points")
        )
        return AdapterResult(
            actor_id=actor_id,
            source="sungjwa_hunter_sim",
            actions=[
                ActionRecord(
                    actor_id=actor_id,
                    action_type="constellation_shift",
                    payload={
                        "object_id": obj.id,
                        "favor_delta": favor_delta,
                        "turn": turn,
                        "source": "sungjwa_hunter_sim",
                    },
                )
            ],
            objects=[obj],
            metadata={"turn": turn, "favor_delta": favor_delta},
        )

    def _pack(
        self,
        actor_id: str,
        obj: CreativeObject,
        kind: str,
        turn: int,
        event: dict[str, Any],
    ) -> AdapterResult:
        validation = self.validator.validate_creative_object(obj.to_dict())
        if not validation.ok:
            raise ValueError(f"invalid sungjwa object: {validation.errors}")
        return AdapterResult(
            actor_id=actor_id,
            source="sungjwa_hunter_sim",
            actions=[
                ActionRecord(
                    actor_id=actor_id,
                    action_type="hunter_event",
                    payload={
                        "object_id": obj.id,
                        "kind": kind,
                        "turn": turn,
                        "source": "sungjwa_hunter_sim",
                    },
                )
            ],
            objects=[obj],
            metadata={"event": event},
        )
