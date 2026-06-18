"""Eldoria fantasy_simulator turn → CPoW ActionRecord + CreativeObject."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cpow_engine.models import ActionRecord, CreativeObject, PropertyDef
from cpow_engine.physics import create_heat_object, create_material_object
from cpow_engine.schema import SchemaValidator


_ACTION_HEAT_MAP: dict[str, float] = {
    "explore": 25.0,
    "rest": 10.0,
    "train": 40.0,
    "craft": 55.0,
    "fight": 90.0,
    "combat": 90.0,
    "build": 45.0,
    "gather": 35.0,
}

_MATERIAL_ACTIONS = frozenset({"craft", "build", "gather", "mine"})


@dataclass
class AdapterResult:
    """Adapter output — actions for CPoW scoring + optional new objects."""

    actor_id: str
    source: str
    actions: list[ActionRecord] = field(default_factory=list)
    objects: list[CreativeObject] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def primary_action(self) -> ActionRecord | None:
        return self.actions[0] if self.actions else None


class FantasyTurnAdapter:
    """Map Eldoria /v1/turn payloads to CPoW data."""

    def __init__(self, validator: SchemaValidator | None = None) -> None:
        self._validator = validator or SchemaValidator()

    def from_turn(
        self,
        actor_id: str,
        action: str,
        turn_result: dict[str, Any] | None = None,
    ) -> AdapterResult:
        turn_result = turn_result or {}
        action_key = action.lower().strip()
        heat = _ACTION_HEAT_MAP.get(action_key, 20.0)

        tension = float(
            turn_result.get("world", {}).get("tension", 0) or 0
        )
        if tension > 50:
            heat *= 1.15

        objects: list[CreativeObject] = []
        if action_key in _MATERIAL_ACTIONS:
            material = str(
                turn_result.get("crafted_item")
                or turn_result.get("material", "iron")
            )
            obj = create_material_object(actor_id, action_key, material)
            objects.append(obj)
            record = ActionRecord(
                actor_id=actor_id,
                action_type="create_object",
                payload={
                    "object_id": obj.id,
                    "label": obj.label,
                    "source": "fantasy_simulator",
                    "eldoria_action": action_key,
                },
            )
        else:
            obj = create_heat_object(actor_id, f"eldoria_{action_key}", heat)
            objects.append(obj)
            record = ActionRecord(
                actor_id=actor_id,
                action_type="create_object",
                payload={
                    "object_id": obj.id,
                    "label": obj.label,
                    "source": "fantasy_simulator",
                    "eldoria_action": action_key,
                },
            )

        for obj in objects:
            validation = self._validator.validate_creative_object(obj.to_dict())
            if not validation.ok:
                raise ValueError(
                    f"adapter produced invalid object: {validation.errors}"
                )

        return AdapterResult(
            actor_id=actor_id,
            source="fantasy_simulator",
            actions=[record],
            objects=objects,
            metadata={
                "eldoria_action": action_key,
                "session_id": turn_result.get("session_id"),
                "combat_active": turn_result.get("combat_active", False),
            },
        )

    def from_session_state(
        self,
        actor_id: str,
        state: dict[str, Any],
    ) -> list[AdapterResult]:
        """Batch-convert inventory/skills hints into CPoW objects (lightweight)."""
        results: list[AdapterResult] = []
        inventory = state.get("inventory", {})
        items = inventory.get("items", []) if isinstance(inventory, dict) else []
        for item in items[:5]:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id", item.get("item_id", "item")))
            obj = CreativeObject(
                creator_id=actor_id,
                label=item_id,
                properties=[
                    PropertyDef("material_type", 0.0, "catalog_item"),
                    PropertyDef("catalog_ref", 1.0, item_id),
                ],
            )
            results.append(
                AdapterResult(
                    actor_id=actor_id,
                    source="fantasy_simulator",
                    actions=[
                        ActionRecord(
                            actor_id=actor_id,
                            action_type="import_catalog_item",
                            payload={"object_id": obj.id, "item_id": item_id},
                        )
                    ],
                    objects=[obj],
                )
            )
        return results
