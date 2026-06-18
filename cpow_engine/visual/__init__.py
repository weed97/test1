"""CreativeObject visual metadata helpers."""

from __future__ import annotations

from typing import Any

from cpow_engine.models import CreativeObject, ObjectVisual, VISUAL_SLOTS

__all__ = [
    "VISUAL_SLOTS",
    "ObjectVisual",
    "extract_visual",
    "visual_from_properties",
    "with_visual",
]


def extract_visual(obj: CreativeObject) -> ObjectVisual | None:
    """Return explicit visual metadata or infer from legacy property names."""
    if obj.visual is not None and obj.visual.glb_url:
        return obj.visual
    return visual_from_properties(obj)


def visual_from_properties(obj: CreativeObject) -> ObjectVisual | None:
    """Map visual_* properties to ObjectVisual (backward-compatible)."""
    glb = obj.get_property("visual_glb_url")
    if glb is None or not glb.unit:
        return obj.visual
    slot_prop = obj.get_property("visual_slot")
    bone_prop = obj.get_property("visual_attach_bone")
    slot = slot_prop.unit if slot_prop and slot_prop.unit else "world_prop"
    if slot not in VISUAL_SLOTS:
        slot = "world_prop"
    return ObjectVisual(
        glb_url=str(glb.unit),
        slot=slot,
        attach_bone=bone_prop.unit if bone_prop and bone_prop.unit else "",
    )


def with_visual(
    obj: CreativeObject,
    glb_url: str,
    *,
    slot: str = "world_prop",
    attach_bone: str = "",
    offset: dict[str, Any] | None = None,
) -> CreativeObject:
    """Attach visual metadata to an object (returns same instance)."""
    if slot not in VISUAL_SLOTS:
        slot = "world_prop"
    obj.visual = ObjectVisual(
        glb_url=glb_url,
        slot=slot,
        attach_bone=attach_bone,
        offset=dict(offset or {}),
    )
    return obj
